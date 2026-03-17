"""ascript MCP 服务主入口。

基于 mcp 官方 Python SDK，通过 SSE 传输方式提供 API 查询服务。
支持 Cursor、Trae 等 AI 编程工具接入。
"""

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from ascript_mcp.api_store import api_store, VALID_PLATFORMS
from ascript_mcp.examples import find_examples


# ------------------------------------------------------------------
# 创建 MCP Server 实例
# ------------------------------------------------------------------

server = Server("ascript-mcp")


# ------------------------------------------------------------------
# 环境搭建指南数据
# ------------------------------------------------------------------

SETUP_GUIDES: dict[str, str] = {
    "android": """\
# Android 平台环境搭建指南

## 1. 安装 AirScript App
- 在 Android 设备上安装 AirScript App
- 下载地址：https://airscript.cn
- 支持 Android 7.0 及以上版本

## 2. 安装 Python 库
```bash
pip install ascript
```

## 3. 连接设备
- 确保手机和电脑在同一局域网，或使用 USB 连接
- 在 AirScript App 中开启服务

## 4. 编写脚本
```python
from ascript.android import action, node
from ascript.android.screen import gp

# 点击屏幕
action.click(500, 800)

# 查找节点
n = node.Selector().text("登录").find()
```

## 5. 运行方式
- 直接在 AirScript App 中运行脚本
- 或通过电脑端远程推送执行

更多文档请访问：https://docs.airscript.cn
""",
    "ios": """\
# iOS 平台环境搭建指南

## 1. 安装 AirScript App
- 在 iOS 设备上安装 AirScript App
- 下载地址：https://airscript.cn
- 支持 iOS 14.0 及以上版本

## 2. 安装 Python 库
```bash
pip install ascript
```

## 3. 连接设备
- 确保 iPhone/iPad 和电脑在同一局域网
- 在 AirScript App 中开启服务

## 4. 编写脚本
```python
from ascript.ios import action, node
from ascript.ios.screen import gp

# 点击屏幕
action.click(200, 400)

# 查找节点
n = node.Selector().label("登录").find()
```

## 5. 运行方式
- 直接在 AirScript App 中运行脚本
- 或通过电脑端远程推送执行

更多文档请访问：https://docs.airscript.cn
""",
    "windows": """\
# Windows 平台环境搭建指南

## 1. 系统要求
- Windows 10 / 11
- Python 3.8 及以上版本

## 2. 安装 Python 库
```bash
pip install ascript
```

## 3. 安装 AirScript 开发工具（可选）
- 下载地址：https://airscript.cn
- 提供可视化的找图找色、窗口检查等辅助工具

## 4. 编写脚本
```python
from ascript.windows.hardware import mouse, keyboard
from ascript.windows.screen import find_images, find_colors
from ascript.windows.window import Window, Selector

# 鼠标点击
mouse.click(500, 300)

# 键盘输入
keyboard.input_text("Hello!")

# 查找窗口
wnd = Selector().title("记事本").find()
```

## 5. 运行方式
```bash
python your_script.py
```

## 6. 打包发布
- 使用 AirScript 工具可以将脚本打包为 exe 可执行文件

更多文档请访问：https://docs.airscript.cn
""",
}


# ------------------------------------------------------------------
# 注册 MCP Tools
# ------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的 MCP 工具。"""
    return [
        Tool(
            name="get_platform_overview",
            description=(
                "Get an overview of all API modules for a given platform (android/ios/windows). "
                "Returns module names, descriptions, and lists of classes/functions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Target platform: 'android', 'ios', or 'windows'",
                        "enum": ["android", "ios", "windows"],
                    }
                },
                "required": ["platform"],
            },
        ),
        Tool(
            name="get_module_apis",
            description=(
                "Get detailed API documentation for a specific module. "
                "Supports fuzzy matching: e.g. 'screen' matches 'ascript.windows.screen'. "
                "Returns full function signatures, parameters, and docstrings."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Target platform: 'android', 'ios', or 'windows'",
                        "enum": ["android", "ios", "windows"],
                    },
                    "module": {
                        "type": "string",
                        "description": (
                            "Module name. Can be full path like 'ascript.windows.screen' "
                            "or short name like 'screen', 'action', 'node'"
                        ),
                    },
                },
                "required": ["platform", "module"],
            },
        ),
        Tool(
            name="search_api",
            description=(
                "Search APIs by keyword across function names, class names, and docstrings. "
                "Useful when you're not sure which module contains the functionality you need."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword, e.g. 'click', 'ocr', 'find_image', '截图'",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Optional. Filter by platform: 'android', 'ios', or 'windows'. Empty string searches all platforms.",
                        "default": "",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_code_example",
            description=(
                "Get runnable code examples for common automation tasks. "
                "Covers clicking, swiping, image finding, color finding, OCR, node finding, keyboard/mouse, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": (
                            "Task keyword, e.g. '点击'(click), '找图'(find image), "
                            "'OCR', '滑动'(swipe), '键盘'(keyboard), '窗口'(window)"
                        ),
                    },
                    "platform": {
                        "type": "string",
                        "description": "Target platform: 'android', 'ios', or 'windows'",
                        "enum": ["android", "ios", "windows"],
                    },
                },
                "required": ["task", "platform"],
            },
        ),
        Tool(
            name="get_setup_guide",
            description=(
                "Get the environment setup and installation guide for a given platform. "
                "Includes installation steps, dependencies, and a quick-start code snippet."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Target platform: 'android', 'ios', or 'windows'",
                        "enum": ["android", "ios", "windows"],
                    }
                },
                "required": ["platform"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理 MCP 工具调用请求。"""
    try:
        if name == "get_platform_overview":
            platform = arguments.get("platform", "")
            result = api_store.get_platform_overview(platform)

        elif name == "get_module_apis":
            platform = arguments.get("platform", "")
            module = arguments.get("module", "")
            if not module:
                result = "错误：请提供要查询的模块名，如 'screen'、'action'、'node' 等。"
            else:
                result = api_store.get_module_apis(platform, module)

        elif name == "search_api":
            query = arguments.get("query", "")
            platform = arguments.get("platform", "")
            if not query:
                result = "错误：请提供搜索关键词。"
            else:
                result = api_store.search_api(query, platform if platform else None)

        elif name == "get_code_example":
            task = arguments.get("task", "")
            platform = arguments.get("platform", "")
            result = find_examples(task, platform)

        elif name == "get_setup_guide":
            platform = arguments.get("platform", "").strip().lower()
            if platform not in SETUP_GUIDES:
                result = f"错误：不支持的平台 '{platform}'。支持的平台：{', '.join(VALID_PLATFORMS)}"
            else:
                result = SETUP_GUIDES[platform]

        else:
            result = f"错误：未知的工具 '{name}'。"

    except Exception as e:
        result = f"内部错误：{type(e).__name__}: {e}"

    return [TextContent(type="text", text=result)]


# ------------------------------------------------------------------
# SSE 传输层与 Starlette 应用
# ------------------------------------------------------------------

sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """SSE 连接入口。"""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def health_check(request: Request):
    """健康检查端点。"""
    return JSONResponse({"status": "ok", "service": "ascript-mcp"})


app = Starlette(
    routes=[
        Route("/health", health_check),
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)


# ------------------------------------------------------------------
# 启动入口
# ------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print("启动 ascript MCP 服务 (SSE 模式)...")
    print("  SSE 端点: http://localhost:8000/sse")
    print("  健康检查: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
