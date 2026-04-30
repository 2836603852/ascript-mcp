# ascript-mcp

<!-- mcp-name: io.github.ascript-cn/ascript-mcp -->

**中文** | [English](./README_EN.md)

[![PyPI](https://img.shields.io/pypi/v/ascript-mcp.svg)](https://pypi.org/project/ascript-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/ascript-mcp.svg)](https://pypi.org/project/ascript-mcp/)

AScript MCP Service — 让 AI 编程工具（Claude Desktop / Cursor / Trae）直接查询 AScript API 文档、操控真实 Android / iOS 设备（iOS 免签免越狱）。

## 功能

- **API 文档查询**：模块概览、API 搜索、代码示例、环境搭建指南
- **在线插件查询**：实时查询 AScript 插件库（OCR、YOLO、HID、大模型等）
- **设备交互**：截图、控件树、OCR、找色、比色、选择器测试
- **开发部署**：创建工程、上传代码、运行、停止、查看日志
- **设备管理**：局域网扫描、ADB 扫描、自动连接

## 安装

```bash
pip install ascript-mcp
```

## 配置 Cursor

### 1. MCP 配置

在项目根目录创建 `.cursor/mcp.json`：

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

### 2. 规则配置

把 [`docs/AGENT_RULES.md`](./docs/AGENT_RULES.md) 完整复制到你的自动化工程根目录的 `.cursorrules`（Cursor）或 `CLAUDE.md` / `AGENTS.md`（Claude Code / 其他 IDE）。

这份规则模板包含：
- 5 阶段标准工作流（先观察 → 选策略 → eval_python 迭代 → 必要时裁图 → 上传运行）
- 选 API 的决策树（控件 → OCR → 找图 → 找色）
- 自动登录 / 签到 / 游戏战斗等常见任务的编排范例
- 反模式清单（凭空猜代码、不验证就 run、硬编码不存在的图片路径等）

> 简版规则（仅当你不想复制完整规则时用）：
> ```
> 当用户需要编写设备自动化脚本（Android/iOS/Windows）时，必须先调用 ascript MCP 的
> get_device_status 与 list_python_packages，再用 eval_python 在设备 REPL 里
> 验证关键代码片段，最后才 upload_file + run_project。
> 禁止凭记忆编写 ascript 代码。
> ```

## 工具列表

### API 文档（5 个）
| 工具 | 说明 |
|------|------|
| `get_platform_overview` | 获取平台 API 模块概览 |
| `get_module_apis` | 获取模块详细 API 文档 |
| `search_api` | 按关键词搜索 API |
| `get_code_example` | 获取代码示例 |
| `get_setup_guide` | 获取环境搭建指南 |

### 在线插件（2 个）
| 工具 | 说明 |
|------|------|
| `list_plugins` | 查询插件库列表 |
| `get_plugin_detail` | 获取插件详细文档 |

### 设备连接（5 个）
| 工具 | 说明 |
|------|------|
| `auto_connect` | 从工程配置自动连接设备 |
| `scan_devices` | 扫描局域网 + ADB 设备 |
| `connect_device` | 手动连接指定设备 |
| `get_device_status` | 获取设备完整运行状态（运行模式/权限/屏幕/电池/内存/正在跑的脚本等，仅 Android） |
| `list_python_packages` | 列出设备 AScript App 已安装的 Python 第三方库（Android + iOS）|

### 观察界面（6 个）
| 工具 | 说明 |
|------|------|
| `screen_capture` | 截取设备屏幕 |
| `dump_ui_tree` | 获取控件树 |
| `test_selector` | 测试选择器是否匹配 |
| `ocr` | 屏幕文字识别 |
| `find_colors` | 多点找色 |
| `compare_colors` | 多点比色 |

### 开发部署（7 个）
| 工具 | 说明 |
|------|------|
| `create_project` | 在设备上创建工程 |
| `upload_file` | 上传文件到设备（自动创建工程） |
| `run_project` | 运行工程 |
| `run_project_debug` | 调试模式运行（Android + ADB），自动 forward 5678 端口并返回 VS Code attach 配置 |
| `stop_project` | 停止运行 |
| `get_run_log` | 获取运行日志 |
| `eval_python` | **设备 Python REPL（Android + iOS）**：直接在主进程 exec 代码立即拿结果，几百毫秒一轮。适合探索调试、复合决策、自定义工作流（SoM/智能 tap/自动裁模板等）。iOS 自动转译 `ascript.android.*` → `ascript.ios.*` 并预加载 cv2/np/Image。详见 [AGENT_EVAL_GUIDE](./docs/AGENT_EVAL_GUIDE.md) |

### 文件管理（2 个）
| 工具 | 说明 |
|------|------|
| `list_projects` | 列出设备上的工程 |
| `get_project_files` | 获取工程文件树 |

## 线上 SSE 模式

如需部署为公网服务（仅 API 文档查询）：

```bash
uvicorn ascript_mcp.server:app --host 0.0.0.0 --port 8000
```

## License

MIT License，详见 [LICENSE](./LICENSE)。Copyright © 2026 北京奥悦科技有限公司。

## 更多信息

- AScript 官网：https://ascript.cn
- API 文档：https://docs.airscript.cn
- 插件库：https://py.airscript.cn
- 社区论坛：https://bbs.ascript.cn
- 京ICP备 2020040944号-4
