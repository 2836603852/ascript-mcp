# ascript-mcp

> **Owned AScript Workspace MCP 1.8.0**: 69 tools, including automatic login, cloud projects/files, AS/IAS/ZIP import/export, developer apps, database/resource listing, and all original device tools.
> Install this checkout with `uv sync --locked` and set `ASCRIPT_CREDENTIALS_FILE`. See [Workspace](docs/WORKSPACE.md) and [tool schemas](docs/TOOLS.md). The upstream README below describes the official PyPI package.

[中文](./README.md) | **English**

**MCP server that lets AI tools (Claude Desktop / Cursor / Trae) control real Android and iOS devices.**

`ascript-mcp` exposes [AScript](https://ascript.cn) — a Python automation platform for Android, iOS, and Windows — as an MCP ([Model Context Protocol](https://modelcontextprotocol.io)) server. AI coding tools can query API docs, inspect live device screens, and deploy scripts to a phone without a jailbreak or Apple developer certificate.

## Why this is interesting

- **Real device control from Claude Desktop / Cursor / Trae** — no emulator, no screen-share tricks, the AI reads actual screenshots and UI trees.
- **iOS without jailbreak or signing** — AScript ships a WebDriverAgent-based bridge that works on stock devices.
- **Physical HID tap hardware (ESP32) supported** — for scenarios where software taps are detected (QA for anti-bot flows, UI tests against hardened apps).
- **25 MCP tools** spanning: API docs, live screenshots, UI tree dump, OCR, color matching, project deploy, run/stop/log.

## Install

```bash
pip install ascript-mcp
```

Python 3.10+.

## Connect from Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ascript": {
      "command": "python",
      "args": ["-m", "ascript_mcp.local"]
    }
  }
}
```

Restart Claude Desktop. You should see 25 new tools under the `ascript` server.

## Connect from Cursor

Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "ascript": {
      "command": "python",
      "args": ["-m", "ascript_mcp.local"]
    }
  }
}
```

And `.cursorrules`:

```
When writing device automation scripts (Android / iOS / Windows),
you MUST use the ascript MCP tools to connect, observe, and query APIs
before writing code. Do not write ascript code from memory.
```

## Connect from Trae

Trae Settings → MCP → Add MCP Server → SSE or stdio, point to `ascript_mcp.local`.

## Available tools

### API documentation (5)
| Tool | Purpose |
|------|---------|
| `get_platform_overview` | List available API modules for a platform |
| `get_module_apis` | Full API docs for a module |
| `search_api` | Search APIs by keyword |
| `get_code_example` | Retrieve curated code examples |
| `get_setup_guide` | Environment setup instructions |

### Plugin registry (2)
| Tool | Purpose |
|------|---------|
| `list_plugins` | Browse the AScript plugin library |
| `get_plugin_detail` | Docs and versions for a specific plugin |

### Device connection (3)
| Tool | Purpose |
|------|---------|
| `auto_connect` | Connect using project config |
| `scan_devices` | Scan LAN and ADB for available devices |
| `connect_device` | Manually connect by IP / serial |

### Live observation (6)
| Tool | Purpose |
|------|---------|
| `screen_capture` | Live screenshot |
| `dump_ui_tree` | Accessibility tree |
| `test_selector` | Validate a selector against the current screen |
| `ocr` | Screen OCR |
| `find_colors` | Multi-point color search |
| `compare_colors` | Multi-point color comparison |

### Project lifecycle (5)
| Tool | Purpose |
|------|---------|
| `create_project` | Create a project on the device |
| `upload_file` | Upload (auto-creates project) |
| `run_project` | Start execution |
| `stop_project` | Stop execution |
| `get_run_log` | Fetch runtime log |

### File management (2)
| Tool | Purpose |
|------|---------|
| `list_projects` | List device projects |
| `get_project_files` | Get project file tree |

## SSE (remote) mode

Deploy as a hosted service (docs queries only; device tools require stdio):

```bash
uvicorn ascript_mcp.server:app --host 0.0.0.0 --port 8000
```

See [`deploy/deploy.md`](./deploy/deploy.md) for systemd + nginx instructions.

## How it works

```
┌──────────────────┐  MCP   ┌──────────────┐  HTTP  ┌─────────────────┐
│ Claude / Cursor  │◄──────►│ ascript-mcp  │◄──────►│ AScript on phone│
│ (MCP client)     │ stdio  │ (this repo)  │        │ (Android / iOS) │
└──────────────────┘        └──────────────┘        └─────────────────┘
```

`ascript-mcp` is the bridge. The phone runs the **AScript app** (free, from [ascript.cn](https://ascript.cn)), which exposes a local HTTP API. Connect over LAN or ADB port-forward.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Bug reports, new code examples, and additional MCP tools are all welcome.

## License

MIT — see [LICENSE](./LICENSE). Copyright © 2026 Beijing Aojoy Technology Co., Ltd. (北京奥悦科技有限公司).

## Links

- Product website: https://ascript.cn
- API docs: https://docs.airscript.cn
- Plugin registry: https://py.airscript.cn
- Community forum: https://bbs.ascript.cn
