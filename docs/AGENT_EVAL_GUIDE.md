# `eval_python` 使用指南（写给 AI / 写给阅读 AI 提示词的人）

本文档描述如何通过 MCP 工具 `eval_python` 在设备的 Python 主进程中执行代码，
以及在编排自动化任务时如何把它和已有 API 配合使用。

整体工作流（5 阶段：观察 → 选策略 → eval 迭代 → 必要时裁图 → 上传跑）请见
[`AGENT_RULES.md`](./AGENT_RULES.md)。本文是 eval 这一步的细化。

---

## 它是什么

`eval_python(code, image_path="")` 把传入的 Python 代码块发送到设备的
AScript App 主进程，立即 `exec()`，从全局变量 `_result` 取值返回。

- **每次调用新建独立 globals 字典**，不会和其他调用、其他工具串话
- **能直接 import `ascript.<platform>.*` 任何子模块**（screen / node / action / system / ui / event / sensor / data ...）
- **几百毫秒一轮**，比 `upload_file + run_project + get_run_log` 快两个数量级
- **Android + iOS 都支持**

### iOS 与 Android 的差异

| 特性 | Android | iOS |
|---|---|---|
| 命名空间 | `ascript.android.*` | `ascript.ios.*` |
| 自动转译 | 无 | 代码里的 `ascript.android.` 自动替换为 `ascript.ios.`，跨平台片段几乎无需改 |
| 预加载 lib | 按需 import | exec 环境里预先注入 `cv2` / `np` / `Image`（PIL），不写 import 也可用 |
| `_im_source` 注入 | 同 | 同；额外：若代码里引用 `img` 变量且 image_path 文件存在，会预读为 cv2 ndarray |
| `airscript.screen.Screen` 兼容 | 原生支持 | 自动把 `Screen.file2Bitmap(path)` 改写为 `PIL.Image.open(path).convert("RGB")` |

完整决策（eval 适用场景 + 例外 + 失败诊断）见下方"⚠ eval 跑在主进程 — 几乎全套 API 可用"小节。

---

## 返回值约定（**重要**）

代码末尾必须把结果赋给 `_result`：

### 1. 简单字符串

```python
_result = "ok"
```

### 2. 结构化数据（推荐）

```python
import json
_result = json.dumps({"found": True, "x": 320, "y": 800})
```

### 3. 含截图（让 AI 多模态查看图）

```python
import json, base64, io
buf = io.BytesIO()
cropped.save(buf, "PNG")
_result = json.dumps({
    "data": {"x": 320, "y": 800, "note": "找到火球术图标"},
    "image_base64": base64.b64encode(buf.getvalue()).decode(),
})
```

MCP 收到字符串后会自动 JSON 解析；含 `image_base64` 字段会被识别为图片返回，
AI 能直接"看见"这张图。

### 4. 错误处理

```python
try:
    ...
    _result = json.dumps({"ok": True, "data": ...})
except Exception as e:
    import traceback
    _result = json.dumps({"ok": False, "error": str(e), "trace": traceback.format_exc()})
```

> ⚠ **未捕获的异常**会导致 App 端 `/api/gp/eval` 返回错误状态码，MCP 会以
> `eval_python 失败` 返回，丢失你的中间结果。建议自己 try/except。

---

## `image_path` 参数

非空时 App 端会自动注入：

```python
_im_source = r"<image_path>"
```

到全局命名空间。这是**沿用已有 GP 工具约定**，让你的代码可以读取已有图片
（如之前自己 capture 保存的截图）而不重新抓屏。

```python
# 调 eval_python(code=..., image_path="/sdcard/airscript/cache/last_screen.png")
# 代码里：
from PIL import Image
im = Image.open(_im_source)
# ...
```

---

## 决策树：找元素该用什么 API

```
任务：操作屏幕上某个元素 X
    │
    ▼
① 控件可达？（dump_ui_tree 有内容 + X 在树里有 text/id/desc）
    是 → 用 node.Selector(...).find().click()           ← 首选
    │
    ▼ 否
② X 上有稳定文字（如"登录"、"领取"、"确定"）？
    是 → 用 Ocr.click(text)                            ← 文字识别次选
    │
    ▼ 否（NPC 名 / 玩家昵称 / 动态文字）
③ X 周围有稳定可视特征（按钮图标、对话框边框、固定背景）？
    是 → 自动裁该特征 → FindImages.find(模板路径)       ← 找图（关键场景）
    │
    ▼ 否
④ 元素是颜色块（HP 条、技能 CD 灰阶、Buff 图标）？
    是 → FindColors.find(...) / FindBlock.find(...)
    │
    ▼ 否
   结合多模式：先 OCR 锚定区域，区域内再找图
```

---

## 常用片段

下面这些片段可以直接放进 `eval_python(code=...)` 的 `code` 参数。
**复制时记得保留 `_result = ...` 那一行**。

### 片段 A：观察当前屏幕全景（截图 + 控件树 + OCR）

```python
import json, base64, io
from ascript.android.screen import capture_pil, Ocr
from ascript.android.node import Selector

# 截图为 PIL.Image
im = capture_pil()

# 转 base64 PNG
buf = io.BytesIO()
im.save(buf, "PNG")
img_b64 = base64.b64encode(buf.getvalue()).decode()

# 控件树（如果可用）
try:
    tree = Selector().dump()
except Exception:
    tree = None

# OCR 全文
try:
    # Ocr.find_all() 返回 list[dict]，键：text/rect/center_x/center_y/confidence；rect=[左,上,右,下]
    texts = Ocr.find_all() or []
    ocr_data = [{"text": t["text"], "rect": t["rect"],
                 "center": [t["center_x"], t["center_y"]]}
                for t in texts]
except Exception:
    ocr_data = []

_result = json.dumps({
    "data": {"ui_tree": tree, "ocr": ocr_data, "screen_size": [im.size[0], im.size[1]]},
    "image_base64": img_b64,
})
```

### 片段 B：按 rect 自动裁模板，存到工程 res/img/auto/

```python
import os, json
from ascript.android.screen import capture, capture_pil
from ascript.android.system import R

PROJECT_AUTO_DIR = R.img("auto")  # 或者直接拼绝对路径
os.makedirs(PROJECT_AUTO_DIR, exist_ok=True)

# 参数（AI 调用前替换）
rect = [290, 790, 350, 850]
name = "skill_fireball"

im = capture_pil()
cropped = im.crop(tuple(rect))
out_path = os.path.join(PROJECT_AUTO_DIR, f"{name}.png")
cropped.save(out_path, "PNG")

_result = json.dumps({
    "ok": True,
    "path": out_path,
    "rect": rect,
    "size": [cropped.size[0], cropped.size[1]],
})
```

### 片段 C：按文字自动裁模板（OCR 驱动）

```python
import os, json
from ascript.android.screen import capture_pil, Ocr
from ascript.android.system import R

text = "登录"
padding = 10

# Ocr 结果是 dict（text/rect/center_x/center_y）；用子串匹配，OCR 文本常带空格/粘连
results = Ocr.find_all() or []
target = next((t for t in results if text in t["text"]), None)
if not target:
    _result = json.dumps({"ok": False, "error": f"未找到文字 {text!r}"})
else:
    l, top, r, b = target["rect"]   # rect = [左,上,右,下]
    rect = (max(0, l - padding), max(0, top - padding),
            r + padding, b + padding)

    PROJECT_AUTO_DIR = R.img("auto")
    os.makedirs(PROJECT_AUTO_DIR, exist_ok=True)
    out_path = os.path.join(PROJECT_AUTO_DIR, f"text_{text}.png")
    capture_pil().crop(rect).save(out_path, "PNG")

    _result = json.dumps({
        "ok": True,
        "path": out_path,
        "rect": list(rect),
        "matched_text": target["text"],
    })
```

### 片段 D：智能 tap（控件 → OCR → 找图 三级 fallback）

```python
import json
from ascript.android.node import Selector
from ascript.android.screen import Ocr, FindImages
from ascript.android import action

target = "登录"  # 文本，AI 写代码前替换
template_path = None  # 可选：图片路径

def try_tap():
    # 1. 控件
    try:
        node = Selector().text(target).find()
        if node:
            node.click()
            return ("node", target)
    except Exception:
        pass
    # 2. OCR
    try:
        if Ocr.click(target):
            return ("ocr", target)
    except Exception:
        pass
    # 3. 找图
    if template_path:
        try:
            r = FindImages.find(template_path)
            if r:
                action.click(r["center_x"], r["center_y"])
                return ("image", template_path)
        except Exception:
            pass
    return (None, None)

method, hit = try_tap()
_result = json.dumps({"ok": method is not None, "method": method, "hit": hit})
```

### 片段 E：等待屏幕变化（动作前后 capture 对比）

```python
import json, time
from ascript.android.screen import capture_cv
import numpy as np

before = capture_cv()
# ... 这里执行某个动作，例如 action.click(...) ...
time.sleep(0.5)
after = capture_cv()

# 简单像素差异
diff = np.abs(before.astype(int) - after.astype(int)).mean()
_result = json.dumps({"changed": float(diff) > 5.0, "diff_mean": float(diff)})
```

### 片段 F：SoM 标注 — 给 AI 一张带编号的截图

```python
import json, base64, io
from PIL import Image, ImageDraw, ImageFont
from ascript.android.screen import capture_pil, Ocr
from ascript.android.node import Selector

im = capture_pil().convert("RGB")
draw = ImageDraw.Draw(im)
elements = []
idx = 1

# 1. 收集 OCR 文字框
for t in (Ocr.find_all() or []):
    rect = tuple(t["rect"])   # Ocr 结果是 dict，rect=[左,上,右,下]
    elements.append({"id": idx, "kind": "ocr", "text": t["text"], "rect": list(rect)})
    draw.rectangle(rect, outline="red", width=2)
    draw.text((rect[0] + 2, rect[1] + 2), str(idx), fill="red")
    idx += 1

# 2. 收集可点控件（如果可用）
try:
    nodes = Selector().clickable(True).find_all() or []
    for n in nodes:
        rc = n.rect  # 节点矩形：node.rect.left/top/right/bottom
        rect = (rc.left, rc.top, rc.right, rc.bottom)
        elements.append({"id": idx, "kind": "node", "text": getattr(n, "text", ""), "rect": list(rect)})
        draw.rectangle(rect, outline="blue", width=2)
        draw.text((rect[0] + 2, rect[1] + 2), str(idx), fill="blue")
        idx += 1
except Exception:
    pass

buf = io.BytesIO(); im.save(buf, "PNG")
_result = json.dumps({
    "data": {"elements": elements, "count": len(elements)},
    "image_base64": base64.b64encode(buf.getvalue()).decode(),
})
```

> AI 拿到这张带 ①②③ 编号的图后，用自然语言挑一个编号，再用对应 `rect` 的中心点击。

---

## ⛔ 最重要：eval 代码无法外部中断

eval 跑在 **App 主进程主线程**。`/api/gp/eval` 的 HTTP 60s 超时只断**客户端连接**，
**服务端 Python 仍在跑**直到代码自然返回。中途**没有 stop_project 这种 kill 手段** ——
代码卡住 → 主线程卡住 → 整个 App UI 冻住，只能等代码出口或用户去后台杀 App 重启。

**所以 eval 代码必须是"自带出口"的防御式编码**：

```python
# ✓ 循环用 range 而不是 while True
for i in range(50):
    if 找到目标:
        break
    time.sleep(0.2)                    # 单次 sleep ≤ 0.5s

# ✓ 显式 deadline，比 60s HTTP 余量充足
import time
deadline = time.time() + 20
while time.time() < deadline:
    ...

# ✓ 网络/IO 必须设 timeout
requests.get(url, timeout=5)

# ✓ 整段 try/except，异常路径也要返回 _result
try:
    ...
    _result = json.dumps({"ok": True, "data": ...})
except Exception as e:
    import traceback
    _result = json.dumps({"ok": False, "error": str(e), "trace": traceback.format_exc()})
```

**禁止**：
- `while True:` 没显式 break
- `time.sleep(N)` N > 5
- 等待用户操作 / 等待屏幕变化 / 等待网络回调（这些用 upload + run_project，可被 stop_project 中断）
- 任何超过 30 秒的逻辑 —— 改 upload + run_project，工程模式跑在 :py 子进程，可立即 kill

---

## 反模式（不要这样做）

❌ 不设 `_result`：返回 `"null"`，AI 拿不到任何信息
❌ `_result` 设成大 PIL Image / numpy 数组：toString 出来一堆乱码，要先 base64 / json
❌ `while True:` 死循环 / `time.sleep > 5s`：eval 无法外部 kill，会卡死 App 主线程
❌ 异常裸奔：try 不包整段，异常吃掉中间结果，且没法定位具体哪行炸
❌ 把工程脚本写在 eval 里：eval 是 ad-hoc 探索/调试工具，工程逻辑应该 upload 上去 run
❌ 在 eval 里等待屏幕变化 / 等待回调：eval 返回后 `_result` 已定，等也等不到 —— 改 upload + run_project

---

## ⚠ eval 跑在主进程 — 几乎全套 API 可用

`/api/gp/eval` 在 App **主进程**跑。Android 主进程 `onCreate` 时已经执行
`App.get().client = ClientBinder.bindClient()`，所以**主进程的 client 是本地 Stub**，
原本走 :py 进程 IPC 的所有 API 在 eval 里也能直接调用（无 IPC，纯本地）。

### eval 能跑的 API（**几乎所有同步 API**）

- 图色全套：`screen.capture / Ocr / FindImages / FindColors / FindBlock / CompareColors / gp_tasks` 等
- 控件检索：`node.Selector` **任何 mode**（0/1/2/3/6/9，无障碍 / 辅助控件 / Root 都行）
- 任何动作：`action.click / slide / gesture / key / touch / IME / hid`
- 数据 / 系统：`data.KeyValue / system.Permission / Sms / Clipboard / Device.getCurrentAppinfo`
- 工具方法：`system.R.*` 路径工具、shell、toast 等
- 第三方：PIL / cv2 / numpy / json / base64 / requests / pandas 等（按 `list_python_packages` 实际查询）

### eval 仍需谨慎的场景（**不是 NPE，是 eval 本身性质决定**）

| 场景 | 为什么 | 应该怎么做 |
|---|---|---|
| 长循环 / 耗时 > 30s | HTTP 60s 是物理上限但只断客户端；服务端代码无法 kill —— 30s 是建议安全边界 | 改用 upload + run_project |
| 阻塞主线程 | eval 在 App 主线程跑，长循环 / 大 sleep 会卡 App UI | 同上 |
| 持续监听回调（event.on / sensor.on / NotificationEvent） | register 能调用，但 eval 返回时 `_result` 已定，回调触发的数据拿不回 | 必须 upload + run_project |
| 长 session（cloud_control 连云、ESP32 BLE HID 持久会话） | 跨多次 eval 共享 session 不可靠 | 工程模式更稳 |
| 任何依赖工程目录上下文的 API | eval 没绑工程根目录（`R.context` / 工程 res 文件） | 工程模式 |

### eval vs upload+run_project 的简单决策规则

```
任务能在 30s 内完成 + 不需要持续监听回调 + 不需要长 session → eval ✓
任务是长循环 / 持续监听 / 跨多步 session                  → upload + run_project
不确定 → 先 eval 试，超时或回调拿不到再切工程模式
```

### eval 失败时怎么诊断

| 失败信号 | 含义 | 应对 |
|---|---|---|
| HTTP 超时（60s） | 代码跑太久 | 改 upload + run_project |
| `_result` 没拿到 / 返回空 | 代码异常没 catch | 在代码外层 try/except 把 `traceback.format_exc()` 放进 `_result` |
| App 卡死 / 屏幕无响应 | eval 阻塞了主线程 | 等 60s HTTP 超时自动恢复，下次改用工程模式跑长任务 |
| 回调注册了但拿不到事件 | eval 返回时回调还没来得及触发 | 持续监听必须用 upload + run_project |

## 与其他 MCP 工具的配合

```
[起步 1]    get_device_status        — 看 run_mode、is_script_running、permissions、屏幕尺寸
[起步 2]    list_python_packages     — 看设备上有哪些第三方 lib 可用（避免 import 不存在）
[初探]      eval_python(片段 A)      — 一次拿全景：截图 + 控件树 + OCR
[资源准备]  eval_python(片段 B/C)    — 自动裁模板存到工程
[写代码]    upload_file              — 把完整脚本 push 到设备
[执行]      run_project              — 跑
[调试]      run_project_debug        — 断点跑
[验证]      get_run_log              — 看输出
[复盘]      eval_python(片段 E)      — 跑完截一帧验证
```

> ⚠ **写 eval_python 代码前先调一次 `list_python_packages`**。AScript App 默认带 opencv-python-headless / numpy / pillow / requests / pandas / openpyxl / pycryptodome / dashscope 等，但具体清单随版本和已装插件变化。AI 凭印象 import 一个不存在的 lib 会让整段 eval 失败。

---

## 安全 / 限制

- HTTP 默认 60s 超时（物理上限），**eval 逻辑预算 ≤ 30s**（参考 deadline 模板用 20s 留余量）
- 设备端 logcat 能看到 `Log.i("GPEval", ...)`，print 不会回到 MCP，要返回信息得放进 `_result`
- 每次 eval 是 fresh globals，**变量不会跨调用保留**，要传递状态请用 `data.KeyValue` 或文件
- App 主进程跑 eval，**不要做长循环**否则会阻塞 App 主线程
