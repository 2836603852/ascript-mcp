# AScript workspace MCP extension

- task_id: backend-extension-20261005
- status: verifying
- owner: current chat
- updated_at: 2026-10-05 21:54 Asia/Shanghai

## Goal and boundaries

Extend the owned AScript MCP with automatic login, cloud project/file operations, source/package import/export, developer app management, database listing, and useful account resources. Replace the installed Codex MCP runtime with this owned version. Preserve existing device tools. The user authorized implementation, testing, commit/push, and runtime replacement. Do not publish, delete production data, or start paid packaging jobs during validation.

## Current position

Repository: local ascript-mcp; origin https://github.com/2836603852/ascript-mcp (public fork); upstream official. Baseline d94508946b4a50986d1f18ff0fe73bcc991a4d40. Owned package is now ascript-mcp-workspace 1.8.0, editable-installed in .venv. Added backend.py, cloud.py, workspace_tools.py and 40 tools; retained the original 29 device/API tools. Automatic admin/cloud sessions and real cloud source/package workflows are verified. Browser owner is current chat, isolated context ascript-backend-analysis; backend pages 2/3, AI Studio page 4.

Evidence: .tmp/live-results.json has 17 passed cloud checks; .tmp/admin-live-result.json has six passed backend checks, including hidden/unpublished app upload, metadata edits and matching package download. All fixtures were deleted and all original production app IDs remain. .tmp/extra-live-result.json verifies all account resource lists, iOS IAS roundtrip, conversations and packaging-link reads. .tmp/mcp-wire-result.json verifies the actual configured command, 69 schemas and six protocol/tool checks. The final unit suite passed 14 cases. .tmp/wheel-result.json verifies a clean wheel installation, all 69 tools and no packaged account file. Credentials/cookies are confined to ignored .local/. Root source download archives real file-tree entries. ZIP/native imports preserve raw CRLF bytes.

Runtime configuration is replaced: Codex server ascript-workspace uses this checkout's .venv Python. Plugin-scoped ascript-local is disabled; the original plugin skill is retained. .tmp/config-result.json confirms all unrelated settings unchanged. This already-initialized chat retains its original catalog; a new chat or supported MCP restart loads the owned connection. Build wheel and sdist completed; public docs and tool schemas are saved.

## Next action

Commit and push the verified implementation to the owned main branch, verify remote commit, then mark this task done and deliver the wheel/report. No more live business checks are required.

## Blockers

None. No production app was changed, no public publishing or paid packaging job was started, and no physical device was controlled. Actual public publish/bulk production update and paid packaging remain untested by design. Git commit/push is the only remaining delivery step.
