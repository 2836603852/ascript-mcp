# AScript Workspace MCP 1.8.0

This owned fork adds automatic developer-console and AI Studio login, cloud source/project operations, package import/export, and account resource listing. It exposes **69 tools**, including the original 29 device/API tools and 40 workspace tools. MIT attribution from the upstream project is retained.

## Installation and credentials

Install this source checkout with `uv sync --locked` or `pip install -e .`. The owned package is named `ascript-mcp-workspace`; this version is installed from source and has not been published to PyPI or the MCP Registry. `server.json` is release metadata, not evidence of a published registry listing.

Copy `account.example.json` to `.local/account.json`, enter your AScript account, and pass its absolute path in `ASCRIPT_CREDENTIALS_FILE`. Credentials can alternatively come from `ASCRIPT_USERNAME` and `ASCRIPT_PASSWORD`. Optional JSON fields `session_dir` and `output_dir` should be absolute paths. `ASCRIPT_OUTPUT_DIR` overrides the output directory. The `.local/` directory is ignored by Git.

Run `.venv/Scripts/python.exe -m ascript_mcp.local` on Windows, or `.venv/bin/python -m ascript_mcp.local` on other platforms. The installed server uses stdio and identifies itself as `ascript-workspace`, version `1.8.0`.

For Codex, register that Python executable as the `ascript-workspace` server, with `ASCRIPT_CREDENTIALS_FILE` in its environment. To replace the old plugin connection while retaining its skill, set:

```toml
[plugins."ascript@ascript".mcp_servers."ascript-local"]
enabled = false
```

The original plugin remains enabled. Do not change unrelated MCPs, models, or client settings. Existing initialized chats can retain their original tool catalog; a new chat or a supported MCP restart loads the new connection.

## Authentication and write semantics

The client keeps separate cookie jars for the developer console and AI Studio. It obtains an SSO token using the official account form, exchanges it at the target service, persists the cookies, and validates the target service itself. The account-center `getUserInfo` endpoint rejected a fresh `source=airscript` token that successfully logged into the developer console, so it is deliberately not the auth success gate.

Every protected operation restores or automatically logs into its service. Read requests can reauthenticate once after explicit session failure. Write requests are never automatically replayed after timeout or auth failure. Their intent and response state are recorded locally in `operations.jsonl`; an unknown result requires reading the target state before retrying. This local journal is evidence for reconciliation, not a claim of server-side idempotency.

Cloud text writes require the revision returned by `cloud_read_file`; stale revisions produce a conflict. Large source files can be read in character ranges or downloaded. Never edit from a truncated fragment as though it were the complete file.

Developer app edits read a fresh form and preserve unrelated current fields. New developer apps default to **unpublished** unless `is_show=true` is explicitly supplied. Public publishing, deletion, device execution, and paid packaging still require authorization for their actual target. Delete tools additionally require `confirm=true`. Merely exposing a tool is not authorization to use it on production data.

## Workflows

| Task | Tools |
|---|---|
| Account and automatic login | `workspace_login`, `workspace_session_status`, `workspace_get_account` |
| Developer app list/detail | `backend_list_apps`, `backend_get_app` |
| Upload, update and visibility | `backend_create_app`, `backend_update_app`, `backend_set_published` |
| Database accounts and other resources | `backend_list_databases`, `backend_get_database`, `backend_list_resources` |
| Cloud project management | `cloud_list_projects`, `cloud_get_project`, `cloud_create_project`, `cloud_rename_project`, `cloud_delete_project` |
| Source and filesystem | `cloud_get_tree`, `cloud_read_file`, `cloud_write_file`, `cloud_create_entry`, `cloud_move_entry`, `cloud_delete_entry`, `cloud_upload_file`, `cloud_download` |
| AS/IAS/ZIP and local directories | `cloud_export_package`, `cloud_import_package`, `cloud_import_directory`, `backend_download_source` |
| Commercial distribution | `cloud_list_apps`, `cloud_publish_app`, `cloud_update_apps`, `cloud_get_package_url` |
| Cloud devices and history | `cloud_get_device`, `cloud_create_pairing`, `cloud_sync_device`, `cloud_disconnect_device`, `cloud_list_conversations`, `cloud_get_conversation` |
| Reconcile uncertain writes | `workspace_operations` |

Developer database tools read account connection details; they do not run SQL or provision a database. Resource listing also supports plugins, Pip extensions, UI templates, detection models, devices, activation codes, usage, recharge history, and device-order history.

Cloud export uses the real server export endpoint and works without a phone. Android AS and iOS IAS export/import roundtrips were verified. The source ZIP produced by `cloud_download` uses the real tree and individual file downloads because the server rejects a root download path. ZIP/native imports preserve source bytes, including CRLF. Directory import skips caches and linked entries and verifies the actual uploaded entrypoint. Download destinations are exclusive unless `overwrite=true` is explicitly selected.

`cloud_get_package_url` obtains the independent-APP packaging entry; it does not start a packaging job or charge the account. The cloud project pairing tools belong to AI Studio and are separate from local USB/Wi-Fi connections.

## Validation

The meaningful unit suite covers form preservation, empty/expanded grids, automatic read reauthentication, non-replayed uncertain writes, explicit revision handling, path validation, and exclusive downloads. CI runs it on Python 3.10, 3.11, and 3.12 alongside the package build.

Real account checks verified login, resource reads, cloud project/file mutation, conflict rejection, source ZIP download, Android AS and iOS IAS roundtrips, local-directory import, hidden/unpublished developer app upload and edits, package download, and fixture cleanup. Production app IDs and their total were preserved. Public publishing, bulk updates to production, paid packaging, and real-device execution were not performed by this release's validation.

On the owner's Windows host, dependency setup, builds, and all tests are launched under a process-tree CPU hard cap of 50%, with hidden child processes. Original ADB subprocess calls now use `CREATE_NO_WINDOW` on Windows. See the generated [tool reference](TOOLS.md) for each schema.
