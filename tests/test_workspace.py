import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from ascript_mcp.backend import WorkspaceClient, WorkspaceError, parse_form, parse_grid
from ascript_mcp.cloud import CloudClient, remote_path
from ascript_mcp.workspace_tools import SPECS, list_workspace_tools


def response(status=200, body="", url="https://as.airscript.cn/admin", content_type="text/html"):
    result = requests.Response()
    result.status_code = status
    result.url = url
    result.headers["Content-Type"] = content_type
    result._content = body.encode() if isinstance(body, str) else body
    result._content_consumed = True
    result.encoding = "utf-8"
    return result


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".tmp"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.client = WorkspaceClient(settings={"username": "fixture", "password": "fixture",
            "session_dir": self.temp.name, "output_dir": self.temp.name})
        self.client.validated = {"admin": time.monotonic(), "cloud": time.monotonic()}

    def tearDown(self):
        self.temp.cleanup()

    def test_form_preserves_successful_controls_and_csrf(self):
        form = parse_form('''<form action="/admin/apply/list/42" method="post">
            <input name="_token" value="csrf"><input name="_method" value="PUT">
            <input name="name" value="A"><input name="fileUrl" type="file">
            <input name="format_ver" type="radio" value="3"><input name="format_ver" type="radio" value="4" checked>
            <input name="is_show" type="hidden" value="off"><input name="other" disabled value="skip">
            <textarea name="desc">&lt;p&gt;unchanged&lt;/p&gt;</textarea>
            <select name="mode"><option value="a">A</option><option selected value="b">B</option></select>
            </form>''', "https://as.airscript.cn/")
        self.assertEqual(form["fields"]["format_ver"], "4")
        self.assertEqual(form["fields"]["desc"], "<p>unchanged</p>")
        self.assertEqual(form["fields"]["is_show"], "off")
        self.assertEqual(form["fields"]["mode"], "b")
        self.assertNotIn("other", form["fields"])
        self.assertEqual(form["file_fields"], ["fileUrl"])

    def test_grid_returns_stable_field_names_and_total(self):
        html = '''<title>数据库</title><div id="pjax-container">总共 12 条
          <table class="grid-table"><thead><tr><th>数据库</th><th>操作</th></tr></thead>
          <tbody><tr><td class="column-db">db_sample</td><td class="column-host">127.0.0.1</td>
          <td><a href="/download">下载</a></td></tr></tbody></table></div>'''
        parsed = parse_grid(html, "https://as.airscript.cn/admin")
        self.assertEqual(parsed["rows"][0]["db"], "db_sample")
        self.assertEqual(parsed["total"], 12)
        self.assertEqual(parsed["rows"][0]["links"][0]["url"], "https://as.airscript.cn/download")

    def test_reads_reauthenticate_once(self):
        session = self.client.sessions["cloud"]
        with patch.object(session, "request", side_effect=[response(401), response(200, '{"projects":[]}', content_type="application/json")]) as request, patch.object(self.client, "login") as login:
            result = self.client.json_request("cloud", "GET", "/api/projects")
        self.assertEqual(result, {"projects": []})
        self.assertEqual(request.call_count, 2)
        login.assert_called_once_with("cloud", force=True)

    def test_empty_and_expanded_grid_rows_are_not_records(self):
        empty='<table class="grid-table"><tbody><tr><td colspan="10">没有数据</td></tr></tbody></table>'
        self.assertEqual(parse_grid(empty,"https://as.airscript.cn/")["rows"],[])
        nested='''<table class="grid-table"><thead><tr><th>ID</th></tr></thead><tbody>
          <tr><td class="column-id">42<table><tbody><tr><td>nested</td></tr></tbody></table></td></tr>
          <tr><td colspan="10">expanded details</td></tr></tbody></table>'''
        self.assertEqual(len(parse_grid(nested,"https://as.airscript.cn/")["rows"]),1)

    def test_mutation_timeout_has_unknown_outcome_and_is_not_retried(self):
        with patch.object(self.client.sessions["cloud"], "request", side_effect=requests.Timeout) as request:
            with self.assertRaises(WorkspaceError) as caught:
                self.client.request("cloud", "POST", "/api/projects", json={"name": "fixture"})
        self.assertEqual(request.call_count, 1)
        self.assertEqual(caught.exception.code, "OPERATION_UNKNOWN")
        self.assertEqual(self.client.operations()[-1]["state"], "unknown")
        self.assertIsNotNone(caught.exception.operation_id)

    def test_mutation_auth_failure_does_not_replay(self):
        with patch.object(self.client.sessions["cloud"], "request", return_value=response(401)) as request, patch.object(self.client, "login") as login:
            with self.assertRaises(WorkspaceError) as caught:
                self.client.request("cloud", "PUT", "/api/projects/x/files", json={"content": "x"})
        self.assertEqual(request.call_count, 1)
        login.assert_not_called()
        self.assertEqual(caught.exception.code, "AUTH_EXPIRED")

    def test_permission_failure_is_not_mistaken_for_expired_session(self):
        with patch.object(self.client.sessions["cloud"], "request", return_value=response(403, '{"message":"denied"}')) as request, patch.object(self.client, "login") as login:
            with self.assertRaises(WorkspaceError) as caught:
                self.client.request("cloud", "GET", "/api/projects")
        login.assert_not_called()
        self.assertEqual(request.call_count, 1)
        self.assertEqual(caught.exception.status, 403)

    def test_download_does_not_overwrite_existing_file(self):
        target = Path(self.temp.name) / "owned.as"
        target.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            self.client.download_response(response(body=b"new"), str(target))
        self.assertEqual(target.read_bytes(), b"existing")

    def test_download_sanitizes_remote_filename(self):
        res = response(body=b"package", content_type="application/octet-stream")
        res.headers["Content-Disposition"] = 'attachment; filename="../../safe.as"'
        saved = self.client.download_response(res)
        self.assertEqual(Path(saved["path"]), Path(self.temp.name) / "safe.as")
        self.assertEqual(Path(saved["path"]).read_bytes(), b"package")

    def test_file_write_preserves_explicit_revision(self):
        cloud = CloudClient(self.client)
        with patch.object(self.client, "json_request", return_value={"revision": "new"}) as request:
            cloud.write_file("test-id", "__init__.py", "print(1)", "previous")
        self.assertEqual(request.call_args.kwargs["json"]["revision"], "previous")

    def test_metadata_update_preserves_unrelated_fields_and_multipart(self):
        html = '''<form action="/admin/apply/list/42"><input name="_token" value="csrf">
            <input name="_method" value="PUT"><input name="name" value="before">
            <input name="is_show" value="off"><input name="desc" value="existing details">
            <input name="format_ver" value="4"></form>'''
        with patch.object(self.client, "request", side_effect=[response(body=html), response(url="https://as.airscript.cn/admin/apply/list")]) as request, patch.object(self.client, "get_app", return_value={"id":42,"fields":{"name":"after","is_show":"off","desc":"existing details","format_ver":"4"}}):
            result=self.client.save_app({"name":"after"},app_id=42)
        packet={key:value[1] for key,value in request.call_args.kwargs["files"]}
        self.assertEqual(packet["desc"],"existing details")
        self.assertEqual(packet["format_ver"],"4")
        self.assertEqual(packet["_method"],"PUT")
        self.assertEqual(packet["_token"],"csrf")
        self.assertTrue(result["saved"])

    def test_create_defaults_to_unpublished_and_reads_back(self):
        package=Path(self.temp.name)/"fixture.as"
        package.write_bytes(b"fixture")
        html='''<form action="/admin/apply/list"><input name="_token" value="csrf">
           <input name="name"><input name="is_show" value="on"><input type="file" name="fileUrl"></form>'''
        with patch.object(self.client,"request",side_effect=[response(body=html),response(url="https://as.airscript.cn/admin/apply/list/43/edit")]) as request, patch.object(self.client,"list_resources",return_value={"rows":[]}), patch.object(self.client,"get_app",return_value={"id":43,"fields":{"name":"draft","is_show":"off"}}):
            result=self.client.save_app({"name":"draft"},package_path=str(package))
        self.assertEqual(request.call_args.kwargs["data"]["is_show"],"off")
        self.assertEqual(result["app_id"],43)
        self.assertTrue(result["saved"])

    def test_invalid_paths_are_rejected_before_any_request(self):
        for path in ("../x", "/x", "C:/x", "a\\b", "a//b", "."):
            with self.subTest(path=path), self.assertRaises(ValueError):
                remote_path(path)
        self.assertEqual(remote_path("res/image.png"), "res/image.png")

    def test_destructive_tools_have_explicit_confirmation(self):
        tools = {tool.name: tool for tool in list_workspace_tools()}
        for name in ("backend_delete_app", "cloud_delete_project", "cloud_delete_entry", "cloud_disconnect_device"):
            self.assertIn("confirm", tools[name].inputSchema["required"])
            self.assertTrue(tools[name].annotations.destructiveHint)
        self.assertEqual(len(tools), len(SPECS))


if __name__ == "__main__":
    unittest.main()
