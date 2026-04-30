"""ascript MCP 本地服务（stdio 模式）。

通过 stdin/stdout 与 Cursor/Trae 等 AI 编程工具通信，
同时提供 API 文档查询和设备实时交互能力。

使用方式：
    python -m ascript_mcp.local

Cursor 配置（.cursor/mcp.json）：
    {
        "mcpServers": {
            "ascript": {
                "command": "python",
                "args": ["-m", "ascript_mcp.local"]
            }
        }
    }
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, ImageContent, Prompt, PromptMessage, PromptArgument

from ascript_mcp.api_store import api_store, VALID_PLATFORMS
from ascript_mcp.examples import find_examples
from ascript_mcp import device as dev


# ------------------------------------------------------------------
# 环境搭建指南（复用 server.py 的数据）
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

## 3. 编写脚本
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

## 4. 运行方式
```bash
python your_script.py
```

更多文档请访问：https://docs.airscript.cn
""",
}


# ------------------------------------------------------------------
# 创建 MCP Server
# ------------------------------------------------------------------

server = Server("ascript-local")

# ------------------------------------------------------------------
# Server Instructions（始终加载，AI 每次对话都能看到）
# ------------------------------------------------------------------

SERVER_INSTRUCTIONS = """\
你是一个 AScript 自动化开发助手，帮用户为 Android/iOS 设备编写自动化脚本。

## 你的能力

你能直接操作用户的设备：看屏幕（截图/控件树/OCR）、测试选择器、部署运行脚本、查看日志。
你还能查询 AScript 全套 API 文档，确保写出的代码参数正确。

## 首要原则
**禁止假设！禁止猜测！** 你不知道 ascript 的 API 长什么样，不知道界面上有什么控件，不知道按钮在哪个坐标。
写任何一行 ascript 代码之前，必须先通过工具获取真实数据。写"假设在xxx位置"、"大概在屏幕右侧"这种代码是严重错误。

## 控件优先原则（极其重要！）
**能用控件选择器就必须用控件选择器，禁止在有控件属性的情况下用坐标点击。**
- dump_ui_tree 返回的控件树中，大部分元素都有 text、id、desc、className 等属性
- 对这些元素，必须用 `node.Selector().text("xxx").find()` 等方式定位，再调用 `.click()`、`.set_text()` 等方法操作
- 控件选择器比坐标更精准、更稳定，不会因为屏幕分辨率不同而失效
- **坐标点击（action.click(x, y)）只允许在以下场景使用：** 控件树中确实找不到目标元素（如游戏自绘界面、WebView 内部元素）
- 如果你用了坐标点击，必须在代码注释中说明为什么不能用控件选择器

## 核心开发原则

**1. 先连设备，再看屏幕，最后写代码**
连接设备的优先级：
  1. 先用 `auto_connect` 从当前工程配置自动连接（最快，无需扫描）
  2. 连接失败了再用 `connect_device` 手动连接（如果用户提供了 IP）
  3. 只有前两种都不行时才用 `scan_devices` 扫描（耗时较长，避免不必要的扫描）
连接后用 screen_capture + dump_ui_tree 观察真实界面。
绝不凭猜测写 node.Selector().text("xxx")，那个 "xxx" 必须来自你亲眼看到的控件树数据。
操作方案优先级：控件选择器（最稳定） > OCR 文字定位 > 找色/找图（兜底）。只有控件树确实没有目标元素时才降级用图色方案。

**2. 场景不对就要求用户配合**
如果当前界面不是目标场景，直接告诉用户你需要什么。
"请打开微信聊天页" / "请发一个测试红包" / "请切到游戏主界面" — 不要在错误场景下硬编码。

**3. 写了就要验证**
上传脚本后必须 run_project → get_run_log 看输出 → screen_capture 看效果。
有错就改，改了就再跑。这个循环直到脚本稳定。

**4. 脚本在设备上独立运行**
实时循环检测（如抢红包、刷广告）必须写在脚本内部。
不要用 MCP 工具做循环控制 — 网络延迟太高，设备端脚本才能做到毫秒级响应。

## 观察界面的方法

| 手段 | 工具 | 能看到 | 看不到 |
|------|------|--------|--------|
| 截图 | screen_capture | 界面全貌、图片内容、视觉布局 | 控件 ID、层级、属性 |
| 控件树 | dump_ui_tree | id/text/type/rect/clickable 等属性 | 图片内容、自绘/游戏元素 |
| OCR | ocr | 屏幕上所有可见文字及坐标 | 控件层级和属性 |
| 选择器测试 | test_selector | 验证选择器是否能匹配到目标控件 | — |

**截图 + 控件树组合使用**是基本功。截图告诉你"界面长什么样"，控件树告诉你"怎么定位它"。

## 不同场景的技术策略

**App 自动化**（微信、抖音、办公类）
→ 优先用 node.Selector（控件树丰富、稳定）
→ dump_ui_tree 观察 → test_selector 验证 → 写 Selector 代码
→ 选择器策略——用最简单的方式定位，灵活组合：
  - 任何属性（text/desc/type/id/clickable/depth 等）都可以链式组合调用
  - 一个属性够唯一就用一个，不够就组合多个，追求最简写法
  - id 有明确含义（如 com.xxx:id/btn_login）→ 可以用
  - id 是无规则字符串（如 a3f8d2、View.14）→ 不要用，可能是动态分配的
  - 部分属性支持正则匹配，善于利用正则处理动态文本（如 text 包含数字、时间等变化部分）
  - 属性不够唯一时，用关系选择器：通过 child/parent/brother 先定位有明确属性的关系控件，再找到目标
  - 先用 get_module_apis 查 Selector 支持的所有属性和方法，再决定怎么组合
  - 用 test_selector 验证选择器是否稳定匹配

**游戏脚本**
→ 游戏界面通常是自绘的，控件树为空或只有一个 SurfaceView/TextureView
→ 核心策略：完全依赖视觉识别，不用控件选择器
→ 开发流程：
  1. 先 dump_ui_tree 确认控件树确实为空（确认是自绘界面）
  2. screen_capture 截图观察界面布局，理解各区域功能（血条、技能栏、背包、地图等）
  3. 让用户配合切换到不同游戏状态（战斗中/主城/背包/商店），每个状态都截图分析
  4. 根据需求选择识别方案：
→ 识别方案选择：
  - **文字识别（OCR）**：血量数字、金币数、倒计时、任务文字、按钮文字
  - **找色（FindColors）**：血条颜色变化、技能冷却状态（灰/亮）、特定 UI 高亮
  - **比色（CompareColors）**：快速判断当前状态（如某个位置是否变色=技能可用）
  - **找图（FindImages）**：固定图标匹配（技能图标、怪物头像、物品图标）
  - **YOLO 目标检测**：复杂场景识别（多个怪物、动态物体），需要用插件 list_plugins 查 Yolov8Ncnn 等
→ 操作方式：全部用坐标，action.click(x, y) / action.swipe(x1,y1,x2,y2)
→ 坐标适配：不同分辨率手机坐标不同，用 screen_capture 获取屏幕尺寸后按比例计算
→ 性能注意：游戏脚本循环频率高，OCR/找图较慢，优先用 CompareColors（最快）做状态判断，必要时才用 OCR/找图
→ 查 get_module_apis 了解 FindColors/FindImages/Ocr/CompareColors 的参数
→ 复杂游戏考虑用 list_plugins 查第三方插件（TomatoOcr 精度更高，Yolov8Ncnn 做目标检测）

**刷广告/重复操作**
→ 核心是循环 + 状态判断
→ 用 OCR 或比色判断当前状态（广告播放中/已结束/出现关闭按钮）
→ 用 CompareColors 做快速状态检测（比 OCR 更快）
→ 设计状态机：等待 → 检测 → 操作 → 等待

**办公自动化**（批量填表、数据录入）
→ 控件树为主，表单控件（EditText/Button）有明确的 id 和 type
→ node.Selector().id("xxx").find() 定位输入框
→ node.set_text() 填入数据
→ 注意滚动：列表外的控件可能不在控件树中，需要先滚动

## 常见陷阱

- **控件还没加载**：点击后界面切换需要时间，加 time.sleep() 或用 Selector.find() 的超时参数
- **弹窗干扰**：权限弹窗、广告弹窗会挡住目标，脚本要能处理
- **坐标适配**：不同分辨率手机坐标不同，优先用控件选择器而非硬编码坐标
- **控件树为空**：先确认无障碍服务是否开启（Android），或 WDA 是否正常（iOS）
- **选择器匹配多个**：用 test_selector 确认只匹配一个，否则加更多条件缩小范围
- **动态 id 陷阱**：很多 App 的控件 id 是动态生成的无规则字符串，每次启动都不同，用这种 id 写选择器会导致脚本下次运行就失效。判断方法：id 看起来像乱码或纯数字序号就不要用

## 脚本规范

**重要：代码运行环境区分！**
- **Android/iOS**：代码运行在手机设备上，不是本地电脑。必须通过 `upload_file` 或 `deploy_and_run` 发到设备执行。设备端 Python 版本是 3.8.6，语法必须兼容 3.8（不能用 match/case、`X | Y` 类型联合等 3.10+ 语法）
- **Windows**：代码直接在本地电脑运行，用户本地 Python 环境执行即可，无需连接设备、无需 upload_file
- 本地安装的 ascript-tip 包只提供代码提示（IDE 补全），不是运行时

**Android/iOS 严格禁止：**
- 禁止在本地终端执行 `python __init__.py` 运行 Android/iOS 脚本
- 禁止执行 `pip install ascript` 安装运行时库（ascript 运行在设备端，本地装不了也没用）
- 禁止用本地 Python 调试 ascript 代码（导入就会报错，因为依赖设备端环境）
- Android/iOS 脚本的唯一执行方式是 `deploy_and_run` 或 `upload_file` + `run_project`
- Windows 脚本不受此限制，可以在本地直接 `python main.py` 运行

**入口文件**：
- Android / iOS：`__init__.py`
- Windows：`main.py`

**Android/iOS 工程结构**：工程本身是一个 Python 包（package），运行时以模块方式导入。
- 多文件时用相对导入：`from . import helper`、`from .utils import xxx`
- 不要用绝对导入（`import helper` 会找不到）
- 资源文件放 `res/` 目录，用 `R.res("文件名")` 获取路径

**开发方式**：
- 如果用户已在 Cursor 中打开了 AScript 工程，优先直接编辑工程目录下的 `__init__.py`，然后用 `upload_file` 同步到设备运行
- 工程名从当前目录名或用户指定获取
- `upload_file` 会自动确保设备上工程存在（不存在则创建），无需手动调 `create_project`
- 只有在用户没有打开工程时，才需要 `create_project` 从零开始

**导入模板**：

Android:
```python
from ascript.android import action, node
from ascript.android.screen import Ocr, FindColors
```

iOS:
```python
from ascript.ios import action, node
from ascript.ios.screen import Ocr, FindColors
```

在不确定 API 用法时，用 search_api 和 get_module_apis 查询，不要猜参数。
"""

server.instructions = SERVER_INSTRUCTIONS


# ------------------------------------------------------------------
# 注册 Prompts
# ------------------------------------------------------------------

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="write_automation",
            description="开始编写设备自动化脚本。AI 会连接设备、观察界面、编写并调试代码。",
            arguments=[
                PromptArgument(
                    name="task",
                    description="你想自动化什么？如 '微信自动抢红包'、'自动刷抖音广告'、'批量填写表单'",
                    required=True,
                ),
                PromptArgument(
                    name="platform",
                    description="目标平台：android 或 ios",
                    required=True,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None) -> list[PromptMessage]:
    if name != "write_automation":
        raise ValueError(f"未知 prompt: {name}")

    task = (arguments or {}).get("task", "自动化任务")
    platform = (arguments or {}).get("platform", "android")

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"我需要为 {platform} 设备编写自动化脚本：{task}\n\n"
                    f"请连接我的设备，观察当前界面，然后帮我实现。"
                ),
            ),
        )
    ]


# ------------------------------------------------------------------
# 注册工具
# ------------------------------------------------------------------

@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的 MCP 工具。"""
    tools = [
        # ── 文档查询工具 ──────────────────────────────────────────
        Tool(
            name="get_platform_overview",
            description=(
                "获取指定平台(android/ios/windows)的 API 模块概览，"
                "包含模块名、描述、类和函数列表。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "目标平台：android、ios 或 windows",
                        "enum": ["android", "ios", "windows"],
                    }
                },
                "required": ["platform"],
            },
        ),
        Tool(
            name="get_module_apis",
            description=(
                "获取指定模块的完整 API 文档，支持模糊匹配。"
                "例如 'screen' 可匹配 'ascript.windows.screen'。"
                "返回函数签名、参数说明和文档。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "目标平台：android、ios 或 windows",
                        "enum": ["android", "ios", "windows"],
                    },
                    "module": {
                        "type": "string",
                        "description": "模块名，如 'screen'、'action'、'node'",
                    },
                },
                "required": ["platform", "module"],
            },
        ),
        Tool(
            name="search_api",
            description=(
                "按关键词搜索 API，覆盖函数名、类名和文档说明。"
                "当不确定功能在哪个模块时使用。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如 'click'、'ocr'、'截图'",
                    },
                    "platform": {
                        "type": "string",
                        "description": "可选，按平台过滤",
                        "enum": ["android", "ios", "windows", ""],
                        "default": "",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_code_example",
            description="获取常见自动化任务的可运行代码示例。",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "任务关键词，如 '点击'、'找图'、'OCR'、'滑动'",
                    },
                    "platform": {
                        "type": "string",
                        "description": "目标平台",
                        "enum": ["android", "ios", "windows"],
                    },
                },
                "required": ["task", "platform"],
            },
        ),
        Tool(
            name="get_setup_guide",
            description="获取指定平台的环境搭建和安装指南。",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "目标平台",
                        "enum": ["android", "ios", "windows"],
                    }
                },
                "required": ["platform"],
            },
        ),

        # ── 设备交互工具 ──────────────────────────────────────────
        Tool(
            name="auto_connect",
            description=(
                "从当前 AScript 工程目录自动连接设备。\n"
                "读取 .vscode/settings.json 中的 ascript.deviceId 和 ascript.platform，自动连接对应设备。\n"
                "VSCode 插件创建工程时会保存这些信息，无需用户手动输入 IP。\n"
                "传入当前工程的根目录路径即可。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "AScript 工程根目录的绝对路径",
                    },
                },
                "required": ["project_path"],
            },
        ),
        Tool(
            name="scan_devices",
            description=(
                "扫描发现所有 AirScript 设备。\n"
                "同时执行：1) 局域网扫描（WiFi 连接的 Android/iOS 设备）"
                "2) ADB 扫描（USB 连接的 Android 设备）。\n"
                "返回所有发现的设备列表。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "局域网扫描端口，默认 9096",
                        "default": 9096,
                    },
                },
            },
        ),
        Tool(
            name="connect_device",
            description=(
                "连接 Android/iOS 设备。连接后才能使用截图、控件树等设备工具。\n"
                "局域网设备传 IP，ADB 设备传序列号并设 connection_mode='ADB'。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "设备 IP 地址（局域网）或 ADB 序列号",
                    },
                    "port": {
                        "type": "integer",
                        "description": "设备端口，默认 9096（ADB 模式忽略此参数）",
                        "default": 9096,
                    },
                    "password": {
                        "type": "string",
                        "description": "设备密码（公网模式下需要），默认为空",
                        "default": "",
                    },
                    "connection_mode": {
                        "type": "string",
                        "description": "连接方式：LocalIP（默认，局域网）或 ADB（USB）",
                        "enum": ["LocalIP", "ADB"],
                        "default": "LocalIP",
                    },
                },
                "required": ["ip"],
            },
        ),
        Tool(
            name="observe_device",
            description=(
                "一次性获取设备当前状态：截图 + 控件树，比分开调用更快。\n"
                "返回截图（PNG 图片）和控件树（Android JSON / iOS XML）。\n"
                "【重要】拿到控件树后，编写代码必须优先使用控件选择器（通过 text/id/className 等属性定位并操作控件），"
                "只有控件树中确实找不到目标元素时才用坐标点击。"
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="deploy_and_run",
            description=(
                "一步完成开发验证循环：上传代码 → 运行 → 收集日志 → 截图验证。\n"
                "代码会上传为 __init__.py（入口文件），工程不存在时自动创建。\n"
                "返回上传结果、运行结果、日志内容和运行后截图。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "工程名称",
                    },
                    "code": {
                        "type": "string",
                        "description": "Python 脚本代码内容",
                    },
                    "log_seconds": {
                        "type": "number",
                        "description": "收集日志的秒数，默认 5",
                        "default": 5.0,
                    },
                },
                "required": ["project_name", "code"],
            },
        ),
        Tool(
            name="screen_capture",
            description=(
                "截取设备当前屏幕。返回 PNG 图片。"
                "用于查看设备当前界面状态。"
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="dump_ui_tree",
            description=(
                "获取设备当前界面的控件树（UI 层级结构）。返回所有控件的 id、text、desc、className、rect、clickable 等属性。\n\n"
                "【Android】调用前必须先调 get_device_status 确认 run_mode，再选对应 mode，否则拿空树：\n"
                "- run_mode.code=accessibility（无障碍模式）→ mode=0/1（简单/复杂），或 2/3（过滤系统层变种）\n"
                "- run_mode.code=root（Root 或激活模式）   → mode=9（root 控件）\n"
                "- run_mode.code=hid（HID 控件 / 辅助控件模式）→ mode=6（辅助控件）\n"
                "- run_mode.code=screen_only（图色模式）   → 无控件树，跳过 dump，走 OCR/找图\n"
                "⚠ Android 命名陷阱：code=\"hid\" 实际是 ASS 枚举（辅助控件，有控件树）；"
                "code=\"screen_only\" 才是图色模式（无控件树）。\n"
                "Selector 实例化要传相同的 mode：node.Selector(mode=<dump 的 mode>)。\n\n"
                "【iOS】只有 WebDriverAgent 一套引擎，不接 mode 参数（传了被忽略），返回 WDA XML。"
                "iOS Selector() 也不接 engine mode；它的 MODE_EQUAL/CONTAINS/MATCHES 是给单个条件的"
                "匹配运算符（如 selector.text(\"x\", mode=MODE_CONTAINS)），别和 Android 混。\n\n"
                "【写 selector 必看】控件树里有 text/id/desc/className 等属性的元素，必须用 node.Selector() 通过属性定位操作，"
                "不要用坐标点击。坐标只用于控件树中确实没有任何可识别属性的元素。\n"
                "Selector 实例化时也要传相同的 mode：node.Selector(mode=<dump 的同一个 mode>)。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "integer",
                        "description": (
                            "控件检索模式（Android），对应 get_device_status 返回的 run_mode.code：\n"
                            "0 = 无障碍 - 简单（仅重要控件，run_mode=accessibility 时常用）\n"
                            "1 = 无障碍 - 复杂（所有控件含布局节点）\n"
                            "2 = 无障碍 - 简单 + 过滤系统层（状态栏/导航栏，推荐）\n"
                            "3 = 无障碍 - 复杂 + 过滤系统层\n"
                            "6 = 辅助控件（run_mode=hid 时用，对应 Selector.MODE_ASS）\n"
                            "9 = Root 控件（run_mode=root 时用，对应 Selector.MODE_ROOT）\n"
                            "Selector 类常量：MODE_ACC_SIMPLE=0 / MODE_ACC_ALL=1 / MODE_ASS=6 / MODE_ROOT=9。"
                        ),
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="test_selector",
            description=(
                "在设备上实时测试 Selector 选择器，验证是否能精准匹配到目标控件。\n"
                "传入过滤条件（text/id/type/desc/clickable），返回匹配到的控件及其完整属性。\n"
                "用于编写代码前验证 node.Selector().text('xxx').find() 等语句是否能定位到正确控件。\n"
                "条件可组合使用，如同时指定 text 和 clickable。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "按文本内容匹配",
                    },
                    "id": {
                        "type": "string",
                        "description": "按资源 ID 匹配，如 'com.tencent.mm:id/xxx'",
                    },
                    "type": {
                        "type": "string",
                        "description": "按控件类型匹配，如 'TextView'、'Button'、'ImageView'",
                    },
                    "desc": {
                        "type": "string",
                        "description": "按内容描述匹配",
                    },
                    "clickable": {
                        "type": "boolean",
                        "description": "是否可点击",
                    },
                    "mode": {
                        "type": "integer",
                        "description": "检索模式（Android）：0=普通，1=复杂，2=简单过滤系统控件",
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="ocr",
            description=(
                "在设备屏幕上执行 OCR 文字识别。"
                "返回识别到的文字、位置坐标和置信度。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "OCR 引擎：mlkit（默认,快）、paddle_v2、paddle_v3（最新）、tess",
                        "enum": ["mlkit", "paddle_v2", "paddle_v3", "tess"],
                        "default": "mlkit",
                    },
                    "rect": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "识别区域 [left, top, right, bottom]，不传则全屏",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "正则表达式过滤结果",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "置信度阈值 0.0-1.0，默认 0.1",
                        "default": 0.1,
                    },
                },
            },
        ),
        Tool(
            name="find_colors",
            description=(
                "多点找色：在屏幕上查找符合颜色条件的坐标。\n"
                "colors 格式：'x,y,#RRGGBB|x,y,#RRGGBB|...'，第一个点为锚点，后续为偏移点。\n"
                "可选带偏差色：'x,y,#RRGGBB-#偏差|...'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "colors": {
                        "type": "string",
                        "description": "颜色描述，如 '100,200,#FF0000|102,200,#00FF00'",
                    },
                    "rect": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "搜索区域 [left, top, right, bottom]",
                    },
                    "diff": {
                        "type": "number",
                        "description": "相似度 0.0-1.0，默认 0.98",
                        "default": 0.98,
                    },
                },
                "required": ["colors"],
            },
        ),
        Tool(
            name="compare_colors",
            description=(
                "多点比色：检查屏幕指定位置的颜色是否匹配。\n"
                "返回布尔值。用于判断界面状态。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "colors": {
                        "type": "string",
                        "description": "颜色描述，如 '100,200,#FF0000|102,200,#00FF00'",
                    },
                    "diff": {
                        "type": "number",
                        "description": "相似度阈值，默认 0.9",
                        "default": 0.9,
                    },
                },
                "required": ["colors"],
            },
        ),
        Tool(
            name="create_project",
            description="在设备上创建新工程。上传文件前需要先创建工程。",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "工程名称（英文/数字/下划线）",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_python_packages",
            description=(
                "列出设备 AScript App 内已安装的 Python 第三方库（Android + iOS）。\n"
                "AI 在写脚本（尤其是 eval_python 片段）前**强烈建议先调用**，"
                "确认要 import 的 lib 在该设备上可用。\n\n"
                "Android: 走 /api/status 的 python.packages（importlib.metadata 实时查询）。\n"
                "iOS:     借 eval_python 跑 importlib.metadata 实时列出。\n\n"
                "常见自带库：opencv-python-headless / numpy / pillow / requests / pandas / "
                "openpyxl / pymysql / websockets / cryptography 等，"
                "具体清单随 App 版本和用户安装的插件而变化，**以本工具实时返回为准**。"
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_device_status",
            description=(
                "获取设备完整运行状态（仅 Android）。一次性返回：\n"
                " - device: 品牌/型号/ABI\n"
                " - system: Android 版本/SDK/语言/时区\n"
                " - screen: 分辨率/dpi/方向\n"
                " - battery / network / storage / memory\n"
                " - permissions: 全部权限授权状态\n"
                " - run_mode: 当前运行模式（root / accessibility / screen_only / hid）— 决定可用的 API 集\n"
                " - runtime: 是否正在跑脚本、当前工程名\n"
                " - tools: 已安装工具配置\n\n"
                "强烈建议生成脚本前先调用：根据 run_mode 选择 API（如 node.find 仅在 accessibility 模式可用），"
                "根据 permissions 决定是否需要先申请权限，根据 runtime.is_script_running 避免互踩。"
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_projects",
            description="列出设备上的所有工程。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="run_project",
            description="在设备上运行指定工程。",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "工程名称",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="stop_project",
            description="停止设备上正在运行的工程。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="eval_python",
            description=(
                "在设备主进程的 Python 上下文中直接 exec 任意代码，立即返回结果（Android + iOS）。\n"
                "几百毫秒一轮，不需要 upload_file/run_project，适合：\n"
                " - 探索性调试：试 selector / 找图 / OCR / 找色 / 一次点击\n"
                " - 复合决策：把'看屏幕→判断→点击'打包一段 Python 一次执行\n"
                " - 自动裁模板、SoM 标注、智能 tap 路由\n"
                " - 任意一次性同步 API 调用：action.click / slide / Selector(任何 mode) /"
                " Permission / KeyValue / Sms / Clipboard 等\n\n"
                "Android 主进程 client 已本地 stub 化（App.java onCreate 时 bindClient），"
                "所有原本走 :py 进程 IPC 的 API 现在 eval 里也能直接调。\n\n"
                "⛔ 红线：eval 代码无法外部中断！HTTP 60s 超时只断客户端连接，服务端 Python\n"
                "仍在跑直到自然返回；卡住 = 整个 App UI 冻住。所有循环必须 range/deadline 限定，\n"
                "sleep ≤ 5s，try/except 整段。超过 30s 的逻辑改用 upload + run_project（可被 stop_project kill）。\n\n"
                "⚠ 仍需谨慎的场景：\n"
                " - 长循环 / 耗时 > 30s：用 upload+run_project\n"
                " - 回调注册（event.on / sensor.on）：register 能调用，但 eval 返回时\n"
                "   _result 已定，回调触发的数据拿不回 — 持续监听必须用 upload+run_project\n"
                " - 长 session（cloud_control 连云、ESP32 BLE HID 持久会话）：建议用工程模式\n\n"
                "完整指南见 docs/AGENT_EVAL_GUIDE.md。\n\n"
                "代码必须把结果赋给 _result 全局变量。返回值约定：\n"
                " - 简单字符串：_result = 'ok'\n"
                " - 结构化数据（推荐）：_result = json.dumps({'found': True, 'x': 320})\n"
                " - 含截图返回：_result = json.dumps({'data': {...}, 'image_base64': '...'})\n"
                "   （MCP 自动识别 image_base64 字段并以图片形式返回给 AI 多模态查看）\n\n"
                "image_path 非空时 App 会注入 _im_source 全局变量指向该图片路径；\n"
                "iOS 上若代码中引用 img 变量，会被预读为 cv2 ndarray。\n\n"
                "跨平台：iOS 端会自动把 `ascript.android.` 替换为 `ascript.ios.`，\n"
                "并预加载 cv2 / np / Image (PIL) 到执行环境，常用片段几乎无需修改。\n"
                "完整 API 参见 search_api / get_module_apis（按 platform 选择）。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的 Python 代码。必须将结果赋给 _result 变量。",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "可选：传入已有图片路径，App 会注入为 _im_source 全局变量。",
                    },
                },
                "required": ["code"],
            },
        ),
        Tool(
            name="run_project_debug",
            description=(
                "以调试模式启动 Android 工程，让脚本可被 VS Code / Cursor 通过 debugpy attach 调试。\n"
                "前提：1) 平台为 Android（iOS 不支持）；2) 设备必须通过 ADB 连接（USB / adb tcpip）。\n"
                "行为：自动 adb forward tcp:5678 → 设备 127.0.0.1:5678 + 调用设备 /api/model/run?debug=1，"
                "设备端 :py 进程进入 listen+wait_for_client 阻塞，等待 IDE attach。\n"
                "返回：本地端口、可直接粘贴到 .vscode/launch.json 的 attach 配置片段、操作提示。\n"
                "用户在 VS Code 按 F5 attach 后，业务从 main 开始运行，断点会被命中。\n"
                "停止调试请调用 stop_project（同时停止业务和调试器）。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "工程名称",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_run_log",
            description=(
                "获取设备运行日志（实时收集指定秒数）。\n"
                "用于查看脚本运行输出、错误信息和 print 内容。\n"
                "建议在 run_project 后调用，查看脚本是否正常运行或有报错。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "description": "收集日志的秒数，默认 3 秒",
                        "default": 3.0,
                    },
                },
            },
        ),
        Tool(
            name="list_plugins",
            description=(
                "查询 AScript 在线插件库，返回所有可用插件列表。\n"
                "插件提供额外能力：OCR（TomatoOcr）、YOLO 目标检测、HID 硬件控制、AI 大模型、蓝牙通信等。\n"
                "按下载量排序，包含插件名、作者、描述。"
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_plugin_detail",
            description=(
                "获取指定插件的详细文档，包括 API 说明、参数、代码示例和版本历史。\n"
                "需要先用 list_plugins 查到插件 id。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "plugin_id": {
                        "type": "integer",
                        "description": "插件 ID（从 list_plugins 返回的 id 字段）",
                    },
                },
                "required": ["plugin_id"],
            },
        ),
        Tool(
            name="get_project_files",
            description="获取设备上指定工程的文件树结构。",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "工程名称",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="upload_file",
            description=(
                "上传文件到设备上的指定工程。"
                "content 为文件内容的 base64 编码。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "工程名称",
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "文件在工程内的相对路径，如 '__init__.py' 或 'res/img/1.png'",
                    },
                    "content_base64": {
                        "type": "string",
                        "description": "文件内容的 base64 编码",
                    },
                },
                "required": ["project_name", "relative_path", "content_base64"],
            },
        ),
    ]
    return tools


# ------------------------------------------------------------------
# 处理工具调用
# ------------------------------------------------------------------

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent]:
    """处理 MCP 工具调用。"""
    try:
        result = _dispatch(name, arguments)
    except Exception as e:
        result = f"错误：{type(e).__name__}: {e}"

    # 截图返回图片
    if name == "screen_capture" and isinstance(result, dict) and "base64" in result:
        return [
            ImageContent(type="image", data=result["base64"], mimeType="image/png"),
            TextContent(type="text", text=f"截图完成，图片大小 {result['size_bytes']} 字节。"),
        ]

    # observe_device：返回截图 + 控件树
    if name == "observe_device" and isinstance(result, dict) and "screenshot" in result:
        contents = []
        ss = result["screenshot"]
        contents.append(ImageContent(type="image", data=ss["base64"], mimeType="image/png"))
        tree = result["ui_tree"]
        tree_text = tree if isinstance(tree, str) else json.dumps(tree, ensure_ascii=False, indent=2)
        contents.append(TextContent(type="text", text=(
            f"截图 {ss['size_bytes']} 字节。\n\n控件树:\n{tree_text}\n\n"
            "---\n"
            "⚠ 提醒：编写代码时，对于控件树中有 text/id/desc/className 等属性的元素，"
            "必须使用 node.Selector() 通过属性定位并操作（如 click/set_text），不要用坐标。"
            "坐标点击仅用于控件树中确实没有可识别属性的元素（如游戏自绘界面）。"
        )))
        return contents

    # eval_python：根据 _format 字段拆图片/文本
    if name == "eval_python" and isinstance(result, dict) and "_format" in result:
        fmt = result["_format"]
        if fmt == "image":
            data = result.get("data") or {}
            data_text = json.dumps(data, ensure_ascii=False, indent=2) if data else "(仅图片，无其他数据)"
            return [
                ImageContent(type="image", data=result["image_base64"], mimeType="image/png"),
                TextContent(type="text", text=f"eval_python 返回（含截图）：\n{data_text}"),
            ]
        if fmt == "json":
            return [TextContent(type="text", text=json.dumps(result["data"], ensure_ascii=False, indent=2))]
        if fmt == "text":
            return [TextContent(type="text", text=result["data"] or "(空)")]
        if fmt == "error":
            err = result.get("error", "未知错误")
            code = result.get("code")
            return [TextContent(type="text", text=f"eval_python 失败 (code={code}): {err}")]

    # deploy_and_run：返回日志 + 截图
    if name == "deploy_and_run" and isinstance(result, dict) and "screenshot" in result:
        contents = []
        ss = result["screenshot"]
        logs = result.get("logs", "")
        upload = result.get("upload", {})
        run = result.get("run", {})
        summary = f"上传: {'成功' if upload.get('code') == 1 else '失败'}\n运行: {'成功' if run.get('code') == 1 else '失败'}\n\n日志:\n{logs}"
        contents.append(TextContent(type="text", text=summary))
        contents.append(ImageContent(type="image", data=ss["base64"], mimeType="image/png"))
        return contents

    # 其他结果统一转文本
    if isinstance(result, dict):
        text = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        text = str(result)

    return [TextContent(type="text", text=text)]


def _dispatch(name: str, args: dict) -> str | dict:
    """根据工具名分发到对应处理函数。"""

    # ── 文档查询 ──────────────────────────────────────────────────
    if name == "get_platform_overview":
        return api_store.get_platform_overview(args["platform"])

    if name == "get_module_apis":
        module = args.get("module", "")
        if not module:
            return "错误：请提供模块名。"
        return api_store.get_module_apis(args["platform"], module)

    if name == "search_api":
        query = args.get("query", "")
        if not query:
            return "错误：请提供搜索关键词。"
        platform = args.get("platform", "") or None
        return api_store.search_api(query, platform)

    if name == "get_code_example":
        return find_examples(args.get("task", ""), args.get("platform", ""))

    if name == "get_setup_guide":
        platform = args.get("platform", "").strip().lower()
        if platform not in SETUP_GUIDES:
            return f"错误：不支持的平台 '{platform}'。支持的平台：{', '.join(VALID_PLATFORMS)}"
        return SETUP_GUIDES[platform]

    # ── 设备交互 ──────────────────────────────────────────────────
    if name == "auto_connect":
        return dev.auto_connect_from_project(args["project_path"])

    if name == "scan_devices":
        port = args.get("port", 9096)
        lan_devices = dev.scan_devices(port=port)
        adb_devices = dev.scan_adb_devices()
        all_devices = lan_devices + adb_devices
        if not all_devices:
            return "未发现 AirScript 设备。请确认：\n- 局域网设备：已开启 AirScript 服务且在同一网络\n- USB 设备：已通过 USB 连接且 adb 可用"
        lines = [f"发现 {len(all_devices)} 台设备：\n"]
        for d in all_devices:
            mode = d.get("connection_mode", "LocalIP")
            if mode == "ADB":
                lines.append(f"  - {d['name']}  序列号: {d['ip']}  连接: USB(ADB)")
            else:
                lines.append(f"  - {d['name']}  IP: {d['ip']}:{d['port']}  平台: {d['platform']}  连接: WiFi")
        lines.append("\n使用 connect_device 连接设备。ADB 设备需设置 connection_mode='ADB'。")
        return "\n".join(lines)

    if name == "connect_device":
        mode = args.get("connection_mode", "LocalIP")
        if mode == "ADB":
            return dev.connect_adb(serial=args["ip"])
        return dev.connect(
            ip=args["ip"],
            port=args.get("port", 9096),
            password=args.get("password", ""),
        )

    if name == "observe_device":
        return dev.observe_device()

    if name == "deploy_and_run":
        return dev.deploy_and_run(
            project_name=args["project_name"],
            code=args["code"],
            log_seconds=args.get("log_seconds", 5.0),
        )

    if name == "screen_capture":
        return dev.screen_capture()

    if name == "dump_ui_tree":
        return dev.dump_ui_tree(mode=args.get("mode", 0))

    if name == "test_selector":
        return dev.test_selector(
            text=args.get("text"),
            id=args.get("id"),
            type=args.get("type"),
            desc=args.get("desc"),
            clickable=args.get("clickable"),
            mode=args.get("mode", 0),
        )

    if name == "ocr":
        return dev.ocr(
            mode=args.get("mode", "mlkit"),
            rect=args.get("rect"),
            pattern=args.get("pattern"),
            confidence=args.get("confidence", 0.1),
        )

    if name == "find_colors":
        return dev.find_colors(
            colors=args["colors"],
            rect=args.get("rect"),
            diff=args.get("diff", 0.98),
        )

    if name == "compare_colors":
        return dev.compare_colors(
            colors=args["colors"],
            diff=args.get("diff", 0.9),
        )

    if name == "create_project":
        return dev.create_project(args["name"])

    if name == "get_device_status":
        return dev.get_device_status()

    if name == "list_python_packages":
        return dev.list_python_packages()

    if name == "list_projects":
        return dev.list_projects()

    if name == "run_project":
        return dev.run_project(args["name"])

    if name == "stop_project":
        return dev.stop_project()

    if name == "eval_python":
        return dev.eval_python(args["code"], image_path=args.get("image_path", ""))

    if name == "run_project_debug":
        result = dev.run_project_debug(args["name"])
        if not result.get("success"):
            return result.get("error", "调试启动失败。")
        lines = [
            f"调试已启动：localhost:{result['local_port']} → 设备 127.0.0.1:{result['remote_port']}",
            "",
            "—— 在 .vscode/launch.json 的 configurations 数组里加入以下片段，按 F5 attach ——",
            result["launch_json"],
            "",
            result["hint"],
        ]
        return "\n".join(lines)

    if name == "get_run_log":
        logs = dev.get_run_log(seconds=args.get("seconds", 3.0))
        if not logs:
            return "（未收集到日志，脚本可能尚未输出或已结束）"
        lines = []
        for log in logs:
            tag = {"e": "ERROR", "o": "OUT", "i": "INFO"}.get(log.get("type", ""), "LOG")
            time_str = log.get("time", "")
            msg = log.get("msg", "")
            lines.append(f"[{tag}] {time_str} {msg}")
        return "\n".join(lines)

    if name == "list_plugins":
        return dev.list_plugins()

    if name == "get_plugin_detail":
        return dev.get_plugin_detail(args["plugin_id"])

    if name == "get_project_files":
        return dev.get_project_files(args["name"])

    if name == "upload_file":
        import base64
        content = base64.b64decode(args["content_base64"])
        return dev.upload_file(args["project_name"], args["relative_path"], content)

    return f"错误：未知工具 '{name}'。"


# ------------------------------------------------------------------
# 启动入口
# ------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main_sync():
    """同步入口，供 pyproject.toml console_scripts 使用。"""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
