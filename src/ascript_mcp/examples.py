"""代码示例数据模块。

提供 Android / iOS / Windows 三个平台常见自动化场景的代码模板，
供 MCP 工具 get_code_example 查询使用。
"""

from typing import Optional


# ------------------------------------------------------------------
# 示例数据定义
# ------------------------------------------------------------------

EXAMPLES: list[dict] = [
    # ===================== Android =====================
    {
        "task": "点击",
        "keywords": ["点击", "click", "tap", "触摸"],
        "platform": "android",
        "code": """\
from ascript.android import action

# 点击屏幕坐标 (500, 800)
action.click(500, 800)

# 长按坐标 (500, 800)，持续 1 秒
action.long_click(500, 800, duration=1000)
""",
    },
    {
        "task": "滑动",
        "keywords": ["滑动", "swipe", "滚动", "scroll", "拖动"],
        "platform": "android",
        "code": """\
from ascript.android import action

# 从 (300, 1000) 滑动到 (300, 400)，耗时 500ms
action.swipe(300, 1000, 300, 400, duration=500)
""",
    },
    {
        "task": "找图",
        "keywords": ["找图", "find_image", "图片识别", "模板匹配", "image"],
        "platform": "android",
        "code": """\
from ascript.android.screen import gp

# 在屏幕上查找图片，返回匹配位置
result = gp.find_image("target.png")
if result:
    print(f"找到图片，位置: ({result.x}, {result.y})")
""",
    },
    {
        "task": "找色",
        "keywords": ["找色", "find_color", "颜色", "color", "找颜色"],
        "platform": "android",
        "code": """\
from ascript.android.screen import color_tools

# 在屏幕范围内查找颜色
point = color_tools.find_color("#FF0000")
if point:
    print(f"找到颜色，位置: ({point.x}, {point.y})")
""",
    },
    {
        "task": "OCR 文字识别",
        "keywords": ["ocr", "文字识别", "识别文字", "文本识别", "recognize"],
        "platform": "android",
        "code": """\
from ascript.android.screen import gp

# 全屏 OCR 识别
results = gp.ocr()
for item in results:
    print(f"文本: {item.text}, 置信度: {item.confidence}")
""",
    },
    {
        "task": "节点查找",
        "keywords": ["节点", "node", "控件", "元素", "ui", "selector", "xpath"],
        "platform": "android",
        "code": """\
from ascript.android import node

# 通过文本查找节点并点击
n = node.Selector().text("登录").find()
if n:
    n.click()

# 通过 id 查找节点
n = node.Selector().id("com.example:id/btn_login").find()

# 通过 className 查找
n = node.Selector().className("android.widget.Button").text("确定").find()
""",
    },
    {
        "task": "输入文本",
        "keywords": ["输入", "input", "文本", "text", "打字", "键入", "ime"],
        "platform": "android",
        "code": """\
from ascript.android import action

# 输入文本内容
action.input_text("Hello, AirScript!")
""",
    },

    # ===================== iOS =====================
    {
        "task": "点击",
        "keywords": ["点击", "click", "tap", "触摸"],
        "platform": "ios",
        "code": """\
from ascript.ios import action

# 点击屏幕坐标 (200, 400)
action.click(200, 400)

# 长按坐标
action.long_click(200, 400, duration=1.0)
""",
    },
    {
        "task": "滑动",
        "keywords": ["滑动", "swipe", "滚动", "scroll", "拖动"],
        "platform": "ios",
        "code": """\
from ascript.ios import action

# 从 (200, 600) 滑动到 (200, 200)
action.swipe(200, 600, 200, 200, duration=0.5)
""",
    },
    {
        "task": "找图",
        "keywords": ["找图", "find_image", "图片识别", "模板匹配", "image"],
        "platform": "ios",
        "code": """\
from ascript.ios.screen import gp

# 在屏幕上查找图片
result = gp.find_image("target.png")
if result:
    print(f"找到图片，位置: ({result.x}, {result.y})")
""",
    },
    {
        "task": "找色",
        "keywords": ["找色", "find_color", "颜色", "color", "找颜色"],
        "platform": "ios",
        "code": """\
from ascript.ios.screen import color_tools

# 查找指定颜色
point = color_tools.find_color("#FF0000")
if point:
    print(f"找到颜色，位置: ({point.x}, {point.y})")
""",
    },
    {
        "task": "OCR 文字识别",
        "keywords": ["ocr", "文字识别", "识别文字", "文本识别", "recognize"],
        "platform": "ios",
        "code": """\
from ascript.ios.screen import gp

# 全屏 OCR 识别
results = gp.ocr()
for item in results:
    print(f"文本: {item.text}, 置信度: {item.confidence}")
""",
    },
    {
        "task": "节点查找",
        "keywords": ["节点", "node", "控件", "元素", "ui", "selector", "xpath"],
        "platform": "ios",
        "code": """\
from ascript.ios import node

# 通过 label 查找节点
n = node.Selector().label("登录").find()
if n:
    n.click()

# 通过 type 查找
n = node.Selector().type("XCUIElementTypeButton").label("确定").find()
""",
    },

    # ===================== Windows =====================
    {
        "task": "鼠标操作",
        "keywords": ["鼠标", "mouse", "点击", "click", "双击", "右键"],
        "platform": "windows",
        "code": """\
from ascript.windows.hardware import mouse

# 移动鼠标到坐标
mouse.move_to(500, 300)

# 单击
mouse.click(500, 300)

# 双击
mouse.double_click(500, 300)

# 右键点击
mouse.right_click(500, 300)
""",
    },
    {
        "task": "键盘操作",
        "keywords": ["键盘", "keyboard", "按键", "key", "输入", "快捷键", "hotkey"],
        "platform": "windows",
        "code": """\
from ascript.windows.hardware import keyboard

# 输入文本
keyboard.input_text("Hello, AirScript!")

# 按下单个键
keyboard.press("enter")

# 组合键 Ctrl+C
keyboard.hotkey("ctrl", "c")

# 组合键 Ctrl+V
keyboard.hotkey("ctrl", "v")
""",
    },
    {
        "task": "找图",
        "keywords": ["找图", "find_image", "图片识别", "模板匹配", "image"],
        "platform": "windows",
        "code": """\
from ascript.windows.screen import find_images

# 在屏幕上查找图片
result = find_images.find("target.png")
if result:
    print(f"找到图片，位置: ({result.x}, {result.y})")
""",
    },
    {
        "task": "找色",
        "keywords": ["找色", "find_color", "颜色", "color", "找颜色"],
        "platform": "windows",
        "code": """\
from ascript.windows.screen import find_colors

# 查找指定颜色
point = find_colors.find_color("#FF0000")
if point:
    print(f"找到颜色，位置: ({point.x}, {point.y})")
""",
    },
    {
        "task": "窗口管理",
        "keywords": ["窗口", "window", "句柄", "hwnd", "最大化", "最小化", "前台"],
        "platform": "windows",
        "code": """\
from ascript.windows.window import Window, Selector

# 通过窗口标题查找窗口
wnd = Selector().title("记事本").find()
if wnd:
    # 将窗口置于前台
    wnd.set_foreground()

    # 获取窗口位置和大小
    rect = wnd.get_rect()
    print(f"窗口位置: {rect}")

    # 最大化窗口
    wnd.maximize()
""",
    },
    {
        "task": "OCR 文字识别",
        "keywords": ["ocr", "文字识别", "识别文字", "文本识别", "recognize"],
        "platform": "windows",
        "code": """\
from ascript.windows.screen import screen_core

# 全屏 OCR 识别
results = screen_core.ocr()
for item in results:
    print(f"文本: {item.text}, 置信度: {item.confidence}")
""",
    },
]


# ------------------------------------------------------------------
# 查询函数
# ------------------------------------------------------------------

def find_examples(task: str, platform: str) -> str:
    """根据任务关键词和平台查找代码示例。

    Args:
        task: 任务描述关键词，如 "点击"、"找图"、"OCR"。
        platform: 平台名称 "android" | "ios" | "windows"。

    Returns:
        格式化后的代码示例文本。
    """
    platform = platform.strip().lower()
    task_lower = task.strip().lower()

    if platform not in ("android", "ios", "windows"):
        return f"错误：不支持的平台 '{platform}'。支持的平台：android, ios, windows"

    if not task_lower:
        return "错误：请提供任务描述关键词，如 '点击'、'找图'、'OCR' 等。"

    matched: list[dict] = []
    for ex in EXAMPLES:
        if ex["platform"] != platform:
            continue
        # 匹配关键词
        if any(kw in task_lower for kw in ex["keywords"]) or task_lower in ex["task"].lower():
            matched.append(ex)

    if not matched:
        # 列出该平台所有可用示例
        available = [ex["task"] for ex in EXAMPLES if ex["platform"] == platform]
        return (
            f"未找到 {platform} 平台下与 '{task}' 相关的代码示例。\n"
            f"可用示例主题：{', '.join(available)}\n"
            f"请尝试使用这些关键词搜索。"
        )

    parts: list[str] = []
    for ex in matched:
        parts.append(
            f"## {ex['task']} ({ex['platform']})\n\n"
            f"```python\n{ex['code'].rstrip()}\n```"
        )

    return "\n\n".join(parts)


def list_all_examples(platform: Optional[str] = None) -> str:
    """列出所有可用的代码示例主题。"""
    if platform:
        platform = platform.strip().lower()
        exs = [ex for ex in EXAMPLES if ex["platform"] == platform]
    else:
        exs = EXAMPLES

    if not exs:
        return "没有找到代码示例。"

    lines: list[str] = []
    current_plat = ""
    for ex in exs:
        if ex["platform"] != current_plat:
            current_plat = ex["platform"]
            lines.append(f"\n### {current_plat.upper()}")
        lines.append(f"  - {ex['task']}")

    return "\n".join(lines)
