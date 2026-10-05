"""AI Studio project, file, package and distribution APIs."""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from .backend import WorkspaceClient, WorkspaceError, positive_id


def project_key(value: str) -> str:
    value = str(value)
    if not value or len(value) > 200 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in value):
        raise ValueError("工程 ID 包含无效字符")
    return quote(value, safe="")


def remote_path(value: str, allow_root: bool = False) -> str:
    if "\\" in value or "\x00" in value or value.startswith("/"):
        raise ValueError("工程路径必须是使用 / 的相对路径")
    if not value and allow_root:
        return ""
    parts = value.split("/")
    if not value or any(p in ("", ".", "..") for p in parts) or ":" in value:
        raise ValueError("工程路径不能包含空段、.、.. 或盘符")
    return str(PurePosixPath(value))


class CloudClient:
    def __init__(self, workspace: WorkspaceClient):
        self.workspace = workspace

    def _path(self, project_id: str, suffix: str = "") -> str:
        return "/api/projects/" + project_key(project_id) + suffix

    def _json(self, method: str, path: str, **kwargs) -> dict:
        return self.workspace.json_request("cloud", method, path, **kwargs)

    def list_projects(self) -> dict:
        return self._json("GET", "/api/projects")

    def get_project(self, project_id: str, include_tree: bool = True) -> dict:
        project_key(project_id)
        project = next((p for p in self.list_projects().get("projects", [])
                        if str(p.get("id")) == str(project_id)), None)
        if not project:
            raise WorkspaceError("账号下未找到该工程。", "PROJECT_NOT_FOUND", 404)
        result = {"project": project}
        if include_tree:
            result["tree"] = self.get_tree(project_id)
        return result

    def create_project(self, name: str, platform: str = "android") -> dict:
        if not name.strip() or len(name) > 48 or "/" in name or "\\" in name:
            raise ValueError("工程名为 1 到 48 个字符，不能包含斜杠")
        if platform not in ("android", "ios"):
            raise ValueError("platform 必须为 android 或 ios")
        return self._json("POST", "/api/projects", json={"name": name, "platform": platform})

    def rename_project(self, project_id: str, name: str) -> dict:
        if not name.strip() or len(name) > 48 or "/" in name or "\\" in name:
            raise ValueError("工程名为 1 到 48 个字符，不能包含斜杠")
        return self._json("PATCH", self._path(project_id), json={"name": name})

    def delete_project(self, project_id: str, confirm: bool = False) -> dict:
        if not confirm:
            raise ValueError("删除需要用户明确授权后设置 confirm=true")
        return self._json("DELETE", self._path(project_id))

    def get_tree(self, project_id: str) -> dict:
        return self._json("GET", self._path(project_id, "/tree"))

    def read_file(self, project_id: str, path: str, offset: int = 0,
                  max_chars: int | None = None) -> dict:
        result = self._json("GET", self._path(project_id, "/files"),
                            params={"path": remote_path(path)})
        if max_chars is not None:
            if offset < 0 or not 1 <= max_chars <= 200000:
                raise ValueError("offset >= 0；max_chars 为 1 到 200000")
            content = result.get("content")
            if isinstance(content, str):
                result.update(content=content[offset:offset + max_chars], total_chars=len(content),
                              offset=offset, truncated=offset > 0 or offset + max_chars < len(content))
        return result

    def write_file(self, project_id: str, path: str, content: str,
                   revision: str | None = None) -> dict:
        path = remote_path(path)
        if revision is None:
            current = self.read_file(project_id, path)
            if current.get("binary"):
                raise ValueError("二进制文件请使用 cloud_upload_file")
            revision = current.get("revision")
        if revision is None:
            raise WorkspaceError("读取结果缺少 revision，不能安全覆盖文件。", "REVISION_MISSING")
        return self._json("PUT", self._path(project_id, "/files"), params={"path": path},
                          json={"content": content, "revision": revision})

    def create_entry(self, project_id: str, name: str, type: str = "file",
                     parent_path: str = "") -> dict:
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError("name 必须为单一文件或目录名")
        if type not in ("file", "directory"):
            raise ValueError("type 必须为 file 或 directory")
        return self._json("POST", self._path(project_id, "/entries"),
                          json={"name": name, "type": type,
                                "parentPath": remote_path(parent_path, allow_root=True)})

    def move_entry(self, project_id: str, source_path: str, destination_path: str) -> dict:
        return self._json("PATCH", self._path(project_id, "/entries"),
                          json={"sourcePath": remote_path(source_path),
                                "destinationPath": remote_path(destination_path)})

    def delete_entry(self, project_id: str, path: str, confirm: bool = False) -> dict:
        if not confirm:
            raise ValueError("删除需要用户明确授权后设置 confirm=true")
        return self._json("DELETE", self._path(project_id, "/entries"),
                          params={"path": remote_path(path)})

    def upload_file(self, project_id: str, path: str, local_path: str,
                    overwrite: bool = False) -> dict:
        source = Path(local_path).resolve()
        if not source.is_file() or source.stat().st_size > 50 * 1024 * 1024:
            raise ValueError("上传文件必须存在且不超过 50 MiB")
        params = {"path": remote_path(path)}
        if overwrite:
            params["overwrite"] = "1"
        with source.open("rb") as fh:
            return self._json("PUT", self._path(project_id, "/upload"), params=params,
                              headers={"Content-Type": "application/octet-stream"}, data=fh)

    def download(self, project_id: str, path: str = "", destination: str | None = None,
                 overwrite: bool = False) -> dict:
        path = remote_path(path, allow_root=True)
        if not path:
            return self.download_project(project_id, destination, overwrite)
        response = self.workspace.request("cloud", "GET", self._path(project_id, "/download"),
                                          params={"path": path}, stream=True)
        return self.workspace.download_response(response, destination, overwrite,
                                                 PurePosixPath(path).name or "project.zip")

    def download_project(self, project_id: str, destination: str | None = None,
                         overwrite: bool = False) -> dict:
        """The server disallows the root download path; archive its real files locally."""
        import tempfile
        metadata = self.get_project(project_id, include_tree=True)
        tree = metadata["tree"].get("tree")
        if not isinstance(tree, list):
            raise WorkspaceError("工程文件树格式不正确。", "INVALID_RESPONSE")
        fallback = Path(str(metadata["project"]["name"])).name + "-source.zip"
        target = Path(destination).resolve() if destination else self.workspace.output_dir / fallback
        if target.is_dir():
            target = target / fallback
        if target.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在：{target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, filename = tempfile.mkstemp(prefix=".ascript-source-", dir=target.parent)
        os.close(handle)
        total, file_count = 0, 0
        def walk(nodes):
            for node in nodes:
                yield node
                yield from walk(node.get("children", []))
        try:
            with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as archive:
                for node in walk(tree):
                    path = remote_path(node["path"])
                    if node["type"] == "directory":
                        archive.writestr(path + "/", b"")
                        continue
                    response = self.workspace.request("cloud", "GET", self._path(project_id, "/download"),
                                                      params={"path": path}, stream=True)
                    try:
                        if "json" in response.headers.get("Content-Type", ""):
                            raise WorkspaceError("源文件下载返回错误 JSON。", "INVALID_DOWNLOAD")
                        with archive.open(path, "w") as output:
                            for chunk in response.iter_content(128 * 1024):
                                total += len(chunk)
                                if total > 100 * 1024 * 1024:
                                    raise ValueError("源码总大小超过 100 MiB")
                                output.write(chunk)
                        file_count += 1
                    finally:
                        response.close()
            digest = hashlib.sha256()
            with open(filename, "rb") as fh:
                for chunk in iter(lambda: fh.read(128 * 1024), b""):
                    digest.update(chunk)
            size = Path(filename).stat().st_size
            if overwrite:
                os.replace(filename, target)
            else:
                os.link(filename, target)
                Path(filename).unlink()
            return {"path": str(target), "filename": target.name, "size_bytes": size,
                    "sha256": digest.hexdigest(), "content_type": "application/zip",
                    "file_count": file_count, "source_bytes": total}
        finally:
            Path(filename).unlink(missing_ok=True)

    def export_package(self, project_id: str, destination: str | None = None,
                       overwrite: bool = False) -> dict:
        project = self.get_project(project_id, include_tree=False)["project"]
        response = self.workspace.request("cloud", "GET", self._path(project_id, "/export"), stream=True)
        fallback = str(project["name"]) + (".ias" if project["platform"] == "ios" else ".as")
        return self.workspace.download_response(response, destination, overwrite, fallback)

    def import_package(self, local_path: str, name: str, platform: str | None = None) -> dict:
        source = Path(local_path).resolve()
        if not source.is_file() or source.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("工程包必须存在且不超过 100 MiB")
        if source.suffix.lower() not in (".as", ".ias", ".zip"):
            raise ValueError("导入包必须为 .as/.ias/.zip")
        if platform is None:
            platform = "ios" if source.suffix.lower() == ".ias" else "android"
        if platform not in ("android", "ios") or not name.strip() or len(name) > 48:
            raise ValueError("platform 或工程名无效")
        with source.open("rb") as fh:
            return self._json("POST", "/api/projects/import", params={"name": name,
                "platform": platform, "filename": source.name}, data=fh,
                headers={"Content-Type": "application/octet-stream"})

    def import_directory(self, local_path: str, name: str, platform: str = "android") -> dict:
        source = Path(local_path).resolve()
        if not source.is_dir() or not (source / "__init__.py").is_file():
            raise ValueError("本地工程目录必须存在并包含 __init__.py")
        # Native ZIP import preserves source bytes, including Windows CRLF.
        ignore = {".git", ".venv", "venv", "node_modules", "__pycache__", ".local", ".tmp"}
        files, directories, total = [], set(), 0
        def linked(item):
            info = item.lstat()
            return item.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)
        for root, dirs, names in os.walk(source, followlinks=False):
            dirs[:] = [d for d in dirs if d not in ignore and not linked(Path(root) / d)]
            for dirname in dirs:
                directories.add((Path(root) / dirname).relative_to(source).as_posix())
            for filename in names:
                item = Path(root) / filename
                if linked(item):
                    continue
                size = item.stat().st_size
                total += size
                if size > 50 * 1024 * 1024 or total > 100 * 1024 * 1024 or len(files) >= 5000:
                    raise ValueError("本地源码超过大小或文件数上限")
                files.append((item.relative_to(source).as_posix(), item))
        import tempfile
        target_dir = self.workspace.state_dir / "imports"
        target_dir.mkdir(exist_ok=True)
        handle, filename = tempfile.mkstemp(suffix=".zip", dir=target_dir)
        os.close(handle)
        created, project_id = None, None
        try:
            with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as archive:
                for directory in sorted(directories):
                    archive.writestr(directory + "/", b"")
                for path, item in files:
                    archive.write(item, path)
            created = self.import_package(filename, name, platform)
            project_id = created["project"]["id"]
            expected = (source / "__init__.py").read_bytes().decode("utf-8")
            if self.read_file(project_id, "__init__.py").get("content") != expected:
                raise WorkspaceError("导入后入口源码与本机不一致。", "IMPORT_MISMATCH")
            return {**created, "uploaded_files": [path for path, _ in files], "source_bytes": total,
                    "verification": "entrypoint_readback"}
        except Exception as exc:
            context = {"project_id": project_id, "project_name": name}
            if isinstance(exc, WorkspaceError):
                exc.context = context
                raise
            raise WorkspaceError(f"源码导入未完成：{type(exc).__name__}",
                                 "IMPORT_PARTIAL", context=context) from exc
        finally:
            Path(filename).unlink(missing_ok=True)

    def list_apps(self) -> dict:
        return self._json("GET", "/api/mini-apps")

    def list_conversations(self, project_id: str) -> dict:
        project_key(project_id)
        return self._json("GET", "/api/conversations", params={"projectId": project_id})

    def get_conversation(self, project_id: str, conversation_id: str) -> dict:
        project_key(project_id)
        return self._json("GET", "/api/conversations/" + project_key(conversation_id),
                          params={"projectId": project_id})

    def publish_app(self, project_id: str, name: str, desc: str = "",
                    is_free: bool = True, is_v4: bool = True) -> dict:
        if not name.strip():
            raise ValueError("小程序名称不能为空")
        return self._json("POST", self._path(project_id, "/publish-mini-app"),
                          json={"name": name, "desc": desc, "is_free": "1" if is_free else "0",
                                "isV4": 1 if is_v4 else 0})

    def update_apps(self, project_id: str, app_ids: list[int], is_v4: bool = True) -> dict:
        if not app_ids:
            raise ValueError("必须明确指定要更新的小程序 ID")
        ids = [positive_id(x) for x in app_ids]
        if len(ids) != len(set(ids)):
            raise ValueError("小程序 ID 不能重复")
        return self._json("POST", self._path(project_id, "/update-mini-apps"),
                          json={"ids": ids, "isV4": 1 if is_v4 else 0})

    def package_url(self, app_id: int) -> dict:
        return self._json("GET", f"/api/mini-apps/{positive_id(app_id)}/package-url")

    def device_status(self, project_id: str) -> dict:
        return self._json("GET", self._path(project_id, "/device"))

    def create_pairing(self, project_id: str) -> dict:
        return self._json("POST", self._path(project_id, "/device-pairings"))

    def sync_device(self, project_id: str, run: bool = False) -> dict:
        return self._json("POST", self._path(project_id, "/device/sync"), json={"run": run})

    def disconnect_device(self, project_id: str, confirm: bool = False) -> dict:
        if not confirm:
            raise ValueError("断开设备需要明确授权并设置 confirm=true")
        return self._json("DELETE", self._path(project_id, "/device"))
