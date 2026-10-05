"""Authenticated AScript developer console, shared sessions, and file transfers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from http.cookiejar import LWPCookieJar
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ADMIN_URL = "https://as.airscript.cn"
CLOUD_URL = "https://ai.ascript.cn"
TOKEN_URL = "https://card.nspirit.cn/api/userCenter/getToken"
RESOURCE_PATHS = {
    "apps": "/admin/apply/list", "databases": "/admin/db/list",
    "plugins": "/admin/plug/list", "pip": "/admin/pip/list",
    "ui_templates": "/admin/ui/list", "models": "/admin/model/list",
    "devices": "/admin/devices/list", "activation_codes": "/admin/card/list",
    "usage": "/admin/use/list", "recharges": "/admin/pay/list",
    "device_orders": "/admin/deviceOrder/list",
}
APP_FIELDS = {"name", "format_ver", "is_free", "pro_card", "card_bind_device",
              "autoBuyDevice", "max_device", "desc", "is_hide", "is_show"}
SWITCH_FIELDS = {"card_bind_device", "autoBuyDevice", "is_hide", "is_show"}


class WorkspaceError(RuntimeError):
    def __init__(self, message: str, code: str = "REQUEST_FAILED", status: int | None = None,
                 operation_id: str | None = None, context: dict | None = None):
        super().__init__(message)
        self.code, self.status, self.operation_id = code, status, operation_id
        self.context = context

    def as_dict(self) -> dict:
        return {"error": str(self), "code": self.code, "status": self.status,
                "operation_id": self.operation_id, "context": self.context}


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _text(element) -> str:
    return " ".join(element.get_text(" ", strip=True).split()) if element else ""


def parse_form(html: str, base_url: str) -> dict:
    """Read successful HTML controls, preserving the backend's current values."""
    soup = _soup(html)
    form = next((f for f in soup.find_all("form") if f.find(attrs={"name": "_token"})), None)
    if form is None:
        raise WorkspaceError("未找到带 CSRF 的后台编辑表单。", "FORM_NOT_FOUND")
    values: dict[str, str | list[str]] = {}
    files, controls = [], []
    for node in form.find_all(["input", "textarea", "select"]):
        name, kind = node.get("name", ""), node.get("type", "text")
        if not name or node.has_attr("disabled"):
            continue
        if kind == "file":
            files.append(name)
            continue
        if kind in ("submit", "reset", "button"):
            continue
        if kind in ("radio", "checkbox") and not node.has_attr("checked"):
            continue
        if node.name == "textarea":
            value: Any = node.get_text()
        elif node.name == "select":
            options = node.find_all("option", selected=True)
            if not options and not node.has_attr("multiple"):
                options = node.find_all("option", limit=1)
            selected = [o.get("value", o.get_text()) for o in options]
            value = selected if node.has_attr("multiple") else (selected[0] if selected else "")
        else:
            value = node.get("value", "on" if kind == "checkbox" else "")
        values[name] = value
        controls.append({"name": name, "type": kind, "required": node.has_attr("required")})
    return {"action": urljoin(base_url, form.get("action", "")),
            "method": form.get("method", "post").upper(), "fields": values,
            "file_fields": files, "controls": controls}


def parse_grid(html: str, base_url: str) -> dict:
    """Convert Laravel-admin grids to compact rows, including links and paging."""
    soup = _soup(html)
    table = soup.select_one("table.grid-table") or soup.select_one("table")
    rows, columns = [], []
    if table:
        headers = table.select("thead th")
        columns = [_text(h) for h in headers]
        body = table.find("tbody", recursive=False)
        for tr in body.find_all("tr", recursive=False) if body else []:
            cells = tr.find_all("td", recursive=False)
            if not cells or (len(cells) == 1 and cells[0].has_attr("colspan")):
                continue
            row = {}
            for i, cell in enumerate(cells):
                classes = cell.get("class", [])
                key = next((c[7:] for c in classes if c.startswith("column-")),
                           columns[i] if i < len(columns) and columns[i] else f"column_{i}")
                if key in ("__row_selector__", "__actions__"):
                    continue
                row[key] = _text(cell)
            row["links"] = [{"label": _text(a), "url": urljoin(base_url, a["href"])}
                            for a in tr.find_all("a", href=True)
                            if not a["href"].startswith("javascript:")]
            rows.append(row)
    container = soup.select_one("#pjax-container") or soup.select_one("section.content") or soup.body
    total = re.search(r"总共\s*(\d+)\s*条", _text(container))
    return {"title": _text(soup.title), "columns": columns, "rows": rows,
            "total": int(total.group(1)) if total else len(rows),
            "next_url": next((urljoin(base_url, a["href"]) for a in soup.select(".pagination a[href]")
                              if _text(a) in ("»", "›", "下一页")), None)}


class WorkspaceClient:
    """Separate developer and AI Studio cookie sessions with lazy automatic login."""

    def __init__(self, credentials_path: str | Path | None = None,
                 settings: dict | None = None):
        path = credentials_path or os.environ.get("ASCRIPT_CREDENTIALS_FILE", "")
        config = dict(settings or {})
        if path and not settings:
            with Path(path).open(encoding="utf-8") as fh:
                config = json.load(fh)
        self.username = os.environ.get("ASCRIPT_USERNAME") or config.get("username", "")
        self.password = os.environ.get("ASCRIPT_PASSWORD") or config.get("password", "")
        default_dir = Path(path).resolve().parent if path else Path.cwd() / ".local"
        self.state_dir = Path(config.get("session_dir", default_dir / "sessions")).resolve()
        self.output_dir = Path(os.environ.get("ASCRIPT_OUTPUT_DIR") or
                               config.get("output_dir", Path.cwd() / "outputs")).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.sessions: dict[str, requests.Session] = {}
        self.validated: dict[str, float] = {}
        for service in ("admin", "cloud"):
            session = requests.Session()
            session.headers.update({"User-Agent": "AScript-Workspace-MCP/1.8.0"})
            jar = LWPCookieJar(str(self.state_dir / f"{service}.cookies"))
            if Path(jar.filename).exists():
                try:
                    jar.load(ignore_discard=True)
                except (OSError, ValueError):
                    pass
            session.cookies = jar
            self.sessions[service] = session

    def _save(self, service: str) -> None:
        jar = self.sessions[service].cookies
        temp = str(jar.filename) + f".{uuid.uuid4().hex}.tmp"
        jar.save(temp, ignore_discard=True, ignore_expires=False)
        os.replace(temp, jar.filename)

    @staticmethod
    def _base(service: str) -> str:
        if service not in ("admin", "cloud"):
            raise ValueError("service 必须为 admin 或 cloud")
        return ADMIN_URL if service == "admin" else CLOUD_URL

    @staticmethod
    def _authenticated(service: str, response: requests.Response) -> bool:
        if response.status_code != 200:
            return False
        if service == "cloud":
            try:
                return response.json().get("authenticated") is True
            except ValueError:
                return False
        return urlparse(response.url).hostname == "as.airscript.cn" and bool(
            _soup(response.text).select_one('a[href$="/admin/apply/list"]'))

    def _check(self, service: str) -> requests.Response:
        path = "/admin" if service == "admin" else "/api/auth/session"
        return self.sessions[service].get(self._base(service) + path, timeout=(10, 30))

    def login(self, service: str = "both", force: bool = False) -> dict:
        selected = ("admin", "cloud") if service == "both" else (service,)
        result = {}
        with self.lock:
            for target in selected:
                self._base(target)
                session = self.sessions[target]
                probe = None if force else self._check(target)
                if probe is not None and self._authenticated(target, probe):
                    self.validated[target] = time.monotonic()
                    result[target] = {"authenticated": True, "restored": True}
                    if target == "cloud":
                        result[target]["user"] = probe.json().get("user")
                    continue
                if not self.username or not self.password:
                    raise WorkspaceError("请在 ASCRIPT_CREDENTIALS_FILE 或环境变量中配置账号密码。", "CREDENTIALS_MISSING")
                token_response = session.post(TOKEN_URL, data={"username": self.username,
                    "password": self.password, "source": "airscript" if target == "admin" else "ai"},
                    timeout=(10, 30))
                token_response.raise_for_status()
                token_data = token_response.json()
                token = token_data.get("data", {}).get("token")
                if token_data.get("code") != 1 or not token:
                    raise WorkspaceError(token_data.get("msg", "登录失败"), "LOGIN_FAILED")
                if target == "admin":
                    exchanged = session.get(ADMIN_URL + "/admin/auth/loginByToken",
                                            params={"token": token}, timeout=(10, 30))
                else:
                    exchanged = session.post(CLOUD_URL + "/api/auth/exchange",
                                              json={"token": token}, timeout=(10, 30))
                if not self._authenticated(target, exchanged):
                    raise WorkspaceError("账号授权未建立有效会话。", "LOGIN_FAILED", exchanged.status_code)
                self._save(target)
                self.validated[target] = time.monotonic()
                result[target] = {"authenticated": True, "restored": False}
                if target == "cloud":
                    result[target]["user"] = exchanged.json().get("user")
        return result

    def ensure(self, service: str) -> None:
        if time.monotonic() - self.validated.get(service, -1000) > 30:
            self.login(service)

    def _journal(self, record: dict) -> None:
        record = {"at": datetime.now(timezone.utc).isoformat(), **record}
        with (self.state_dir / "operations.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def operations(self, limit: int = 20) -> list[dict]:
        if not 1 <= limit <= 200:
            raise ValueError("limit 必须在 1 到 200 之间")
        path = self.state_dir / "operations.jsonl"
        if not path.exists():
            return []
        from collections import deque
        with path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in deque(fh, maxlen=limit)]

    def request(self, service: str, method: str, path: str, **kwargs) -> requests.Response:
        """Replay only read requests after session expiry; mutations are never replayed."""
        with self.lock:
            base = self._base(service)
            if not path.startswith("/") or path.startswith("//"):
                raise ValueError("API path 必须为本站相对路径")
            self.ensure(service)
            method = method.upper()
            mutation = method not in ("GET", "HEAD", "OPTIONS")
            operation_id = uuid.uuid4().hex if mutation else None
            if mutation:
                digest = hashlib.sha256(repr({k: v for k, v in kwargs.items()
                                             if k not in ("files", "headers")}).encode()).hexdigest()
                self._journal({"operation_id": operation_id, "state": "prepared", "service": service,
                               "method": method, "path": path, "payload_sha256": digest})
            kwargs.setdefault("timeout", (10, 60))
            try:
                response = self.sessions[service].request(method, base + path, **kwargs)
            except requests.RequestException as exc:
                if mutation:
                    self._journal({"operation_id": operation_id, "state": "unknown", "path": path})
                    raise WorkspaceError("写请求连接中断，结果未知；请先读取目标状态再决定是否重试。",
                                         "OPERATION_UNKNOWN", operation_id=operation_id) from exc
                raise WorkspaceError(f"读取请求失败：{type(exc).__name__}", "NETWORK_ERROR") from exc
            auth_failed = response.status_code == 401 or (
                service == "admin" and ("u.aojoy.vip/login" in response.url or
                                         "/admin/auth/login" in response.url))
            if auth_failed and not mutation:
                self.login(service, force=True)
                response.close()
                response = self.sessions[service].request(method, base + path, **kwargs)
            if auth_failed and mutation:
                self.validated.pop(service, None)
                self._journal({"operation_id": operation_id, "state": "auth_rejected", "path": path})
                raise WorkspaceError("会话已失效，写请求没有自动重发。请重新读取目标状态。",
                                     "AUTH_EXPIRED", response.status_code, operation_id)
            if response.status_code >= 400:
                try:
                    detail = response.json()
                    message = detail.get("message") or detail.get("msg") or str(detail)[:500]
                except ValueError:
                    message = _text(_soup(response.text).title) or f"HTTP {response.status_code}"
                if mutation:
                    state = "unknown" if response.status_code >= 500 else "rejected"
                    self._journal({"operation_id": operation_id, "state": state,
                                   "status": response.status_code, "path": path})
                raise WorkspaceError(message, "HTTP_ERROR", response.status_code, operation_id)
            self._save(service)
            if mutation:
                self._journal({"operation_id": operation_id, "state": "responded",
                               "status": response.status_code, "path": path})
            return response

    def json_request(self, service: str, method: str, path: str, **kwargs) -> dict:
        response = self.request(service, method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise WorkspaceError("接口没有返回有效 JSON。", "INVALID_RESPONSE", response.status_code) from exc

    def session_status(self) -> dict:
        return self.login("both")

    def account(self) -> dict:
        return self.json_request("cloud", "GET", "/api/auth/session")

    def list_resources(self, resource: str, page: int = 1, per_page: int = 20,
                       filters: dict | None = None) -> dict:
        if resource not in RESOURCE_PATHS:
            raise ValueError(f"resource 必须为 {', '.join(RESOURCE_PATHS)}")
        if page < 1 or not 1 <= per_page <= 100:
            raise ValueError("page >= 1，per_page 在 1 到 100 之间")
        params = dict(filters or {})
        if any(k.startswith("_") for k in params):
            raise ValueError("筛选参数不能覆盖后台控制字段")
        params.update(page=page, per_page=per_page)
        response = self.request("admin", "GET", RESOURCE_PATHS[resource], params=params)
        parsed = parse_grid(response.text, response.url)
        return {"resource": resource, "page": page, "per_page": per_page, **parsed}

    def get_app(self, app_id: int) -> dict:
        app_id = positive_id(app_id)
        response = self.request("admin", "GET", f"/admin/apply/list/{app_id}/edit")
        form = parse_form(response.text, response.url)
        fields = {k: v for k, v in form["fields"].items() if not k.startswith("_")}
        soup = _soup(response.text)
        source = next((urljoin(response.url, a["href"]) for a in soup.find_all("a", href=True)
                       if "源码下载" in _text(a)), None)
        return {"id": app_id, "fields": fields, "file_fields": form["file_fields"],
                "source_url": source, "edit_url": response.url}

    def save_app(self, fields: dict, app_id: int | None = None,
                 package_path: str | None = None) -> dict:
        unknown = set(fields) - APP_FIELDS
        if unknown:
            raise ValueError(f"不支持的字段：{', '.join(sorted(unknown))}")
        app_id = positive_id(app_id) if app_id is not None else None
        page = f"/admin/apply/list/{app_id}/edit" if app_id else "/admin/apply/list/create"
        response = self.request("admin", "GET", page)
        form = parse_form(response.text, response.url)
        values = dict(form["fields"])
        if app_id is None:
            values["is_show"] = "off"
        for key, value in fields.items():
            if key in SWITCH_FIELDS:
                if value not in (True, False, "on", "off"):
                    raise ValueError(f"{key} 必须为 boolean 或 on/off")
                value = "on" if value is True or value == "on" else "off"
            if key == "format_ver" and str(value) not in ("3", "4"):
                raise ValueError("format_ver 必须为 3 或 4")
            if key == "is_free" and str(value) not in ("0", "1"):
                raise ValueError("is_free 必须为 0 或 1")
            values[key] = str(value)
        if not values.get("name"):
            raise ValueError("小程序名称不能为空")
        package = Path(package_path).resolve() if package_path else None
        if app_id is None and package is None:
            raise ValueError("新增小程序必须提供程序包")
        if package and (not package.is_file() or package.suffix.lower() not in (".as", ".ias", ".was", ".iuas")):
            raise ValueError("程序包必须为存在的 .as/.ias/.was/.iuas 文件")
        if package and package.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("程序包不能超过 100 MiB")
        action = urlparse(form["action"])
        if action.hostname != "as.airscript.cn":
            raise WorkspaceError("表单目标不属于 AScript 后台。", "INVALID_RESPONSE")
        before_ids = set()
        if app_id is None:
            before_ids = {row.get("id") for row in self.list_resources("apps", per_page=100,
                         filters={"name": values["name"]})["rows"]}
        if package:
            with package.open("rb") as fh:
                result = self.request("admin", "POST", action.path, data=values,
                                      files={"fileUrl": (package.name, fh, "application/octet-stream")})
        else:
            # Preserve the browser's multipart contract even when changing only metadata.
            result = self.request("admin", "POST", action.path,
                                  files=[(k, (None, v)) for k, v in values.items()])
        errors = [_text(x) for x in _soup(result.text).select(".has-error .help-block, .alert-danger")]
        if errors:
            raise WorkspaceError("; ".join(errors), "VALIDATION_FAILED", result.status_code)
        if app_id:
            verified = self.get_app(app_id)
            mismatches = {k: {"expected": values[k], "actual": verified["fields"].get(k)}
                          for k in fields if str(verified["fields"].get(k, "")) != values[k]}
            if mismatches:
                return {"saved": False, "verification": "mismatch", "mismatches": mismatches,
                        "app": verified, "response_url": result.url}
            return {"saved": True, "verification": "readback", "app": verified}
        created_id = re.search(r"/admin/apply/list/(\d+)(?:/edit)?(?:\?|$)", result.url)
        new_id = int(created_id.group(1)) if created_id else None
        if new_id is None:
            candidates = [row for row in self.list_resources("apps", per_page=100,
                          filters={"name": values["name"]})["rows"]
                          if row.get("name") == values["name"] and row.get("id") not in before_ids]
            if len(candidates) == 1 and str(candidates[0].get("id", "")).isdigit():
                new_id = int(candidates[0]["id"])
        if new_id:
            verified = self.get_app(new_id)
            matches = all(str(verified["fields"].get(k, "")) == values[k]
                          for k in set(fields) | {"is_show"})
            return {"saved": matches, "app_id": new_id, "app": verified,
                    "verification": "readback" if matches else "mismatch"}
        return {"submitted": True, "response_url": result.url, "app_id": None,
                "verification": "requires_list_reconciliation"}

    def delete_app(self, app_id: int, confirm: bool = False) -> dict:
        if not confirm:
            raise ValueError("删除需要用户明确授权后设置 confirm=true")
        app_id = positive_id(app_id)
        page = self.request("admin", "GET", f"/admin/apply/list/{app_id}/edit")
        fields = parse_form(page.text, page.url)["fields"]
        return self.json_request("admin", "POST", f"/admin/apply/list/{app_id}",
                                 data={"_method": "delete", "_token": fields["_token"]})

    def download_response(self, response: requests.Response, destination: str | None = None,
                          overwrite: bool = False, fallback: str = "download.bin") -> dict:
        if "json" in response.headers.get("Content-Type", ""):
            raise WorkspaceError("下载接口返回 JSON 而非文件：" + str(response.json())[:500], "INVALID_DOWNLOAD")
        disposition = response.headers.get("Content-Disposition", "")
        match = re.search(r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)", disposition, re.I)
        filename = unquote((match.group(1) or match.group(2)).strip()) if match else fallback
        filename = Path(filename.replace("\\", "/")).name or fallback
        target = Path(destination).expanduser().resolve() if destination else self.output_dir / filename
        if target.is_dir():
            target = target / filename
        if target.exists() and not overwrite:
            response.close()
            raise FileExistsError(f"目标文件已存在：{target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        maximum = 100 * 1024 * 1024
        if int(response.headers.get("Content-Length", "0")) > maximum:
            response.close()
            raise ValueError("下载文件超过 100 MiB")
        temp_path = None
        digest, size = hashlib.sha256(), 0
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".ascript-", delete=False) as fh:
                temp_path = Path(fh.name)
                for chunk in response.iter_content(128 * 1024):
                    size += len(chunk)
                    if size > maximum:
                        raise ValueError("下载文件超过 100 MiB")
                    digest.update(chunk)
                    fh.write(chunk)
            if overwrite:
                os.replace(temp_path, target)
            else:
                os.link(temp_path, target)  # Exclusive destination creation, including concurrent callers.
                temp_path.unlink()
            return {"path": str(target), "filename": target.name, "size_bytes": size,
                    "sha256": digest.hexdigest(), "content_type": response.headers.get("Content-Type")}
        finally:
            response.close()
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def download_source(self, app_id: int, destination: str | None = None,
                        overwrite: bool = False) -> dict:
        app = self.get_app(app_id)
        url = app.get("source_url")
        if not url or urlparse(url).scheme not in ("https", "http"):
            raise WorkspaceError("小程序没有可下载的源码包。", "SOURCE_NOT_FOUND")
        # Cookies remain scoped by the jar; no developer credentials are copied to file hosts.
        response = self.sessions["admin"].get(url, stream=True, timeout=(10, 60))
        response.raise_for_status()
        return self.download_response(response, destination, overwrite,
                                      Path(urlparse(url).path).name)


def positive_id(value: int) -> int:
    if isinstance(value, bool) or int(value) < 1:
        raise ValueError("ID 必须为正整数")
    return int(value)


_client: WorkspaceClient | None = None
_client_lock = threading.Lock()


def get_client() -> WorkspaceClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = WorkspaceClient()
    return _client
