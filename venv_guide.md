# Python 虚拟环境使用指南

## 为什么需要虚拟环境？

虚拟环境是一个**独立的 Python 运行空间**，装在里面的包不会影响全局 Python，也不会被其他项目干扰。
简单理解：**全局 Python 是公共仓库，虚拟环境是项目自己的私人仓库**。

---

## 核心概念

```
全局 Python:     /usr/local/python3.13/bin/python3.13
全局 pip:        /usr/local/python3.13/bin/pip3.13
                  ↓ 创建虚拟环境
虚拟环境 Python:  /opt/ascript-mcp/.venv/bin/python
虚拟环境 pip:     /opt/ascript-mcp/.venv/bin/pip
```

**关键规则：用哪个 pip 装的包，只有对应的 python 能用。**
- 全局 pip 装的包 → 全局 python 能用
- 虚拟环境 pip 装的包 → 虚拟环境 python 能用
- **两者互不相通！**

---

## 第一步：用全局 Python 创建虚拟环境

```bash
cd /opt/ascript-mcp

# 用全局 Python 创建虚拟环境（只需执行一次）
/usr/local/python3.13/bin/python3.13 -m venv .venv
```

执行后会生成 `.venv/` 目录，里面有独立的 python 和 pip。

---

## 第二步：使用虚拟环境（两种方式）

### 方式一：activate 激活（推荐，最省事）

```bash
# 激活虚拟环境
source /opt/ascript-mcp/.venv/bin/activate

# 激活后，终端提示符前面会出现 (.venv)
# 此时 python 和 pip 自动指向虚拟环境的版本

# 验证一下（应该指向 .venv 目录）
which python
# 输出: /opt/ascript-mcp/.venv/bin/python

which pip
# 输出: /opt/ascript-mcp/.venv/bin/pip

# 现在可以直接用 pip 和 python，都是虚拟环境的
pip install -r requirements.txt
python -m ascript_mcp.server

# 用完后退出虚拟环境
deactivate
```

**activate 之后：**
- `python` = 虚拟环境的 python ✅
- `pip` = 虚拟环境的 pip ✅
- `/usr/local/python3.13/bin/python3.13` = 仍然是全局 python ❌（不要用这个！）

### 方式二：不 activate，直接用完整路径

```bash
# 不需要 activate，直接用虚拟环境的完整路径

# 安装依赖
/opt/ascript-mcp/.venv/bin/pip install -r requirements.txt

# 启动服务
/opt/ascript-mcp/.venv/bin/python -m ascript_mcp.server
```

---

## 常见错误

### ❌ 错误：activate 了但用全局 Python 启动

```bash
source .venv/bin/activate               # 激活了 venv
pip install -r requirements.txt         # 包装到了 venv 里 ✅
/usr/local/python3.13/bin/python3.13 -m ascript_mcp.server  # 用全局 Python 启动 ❌
# 报错：ModuleNotFoundError: No module named 'mcp'
# 原因：包在 venv 里，全局 Python 找不到
```

**正确做法：**
```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m ascript_mcp.server            # 直接用 python，不要写完整路径
```

### ❌ 错误：没 activate 就用 pip

```bash
pip install -r requirements.txt         # 这个 pip 可能是全局的，也可能没有
# 不确定装到了哪里
```

**正确做法：**
```bash
source .venv/bin/activate               # 先激活
pip install -r requirements.txt         # 现在确定是 venv 的 pip
```

---

## 本项目完整部署流程

```bash
# 1. 进入项目目录
cd /opt/ascript-mcp

# 2. 创建虚拟环境（首次部署才需要）
/usr/local/python3.13/bin/python3.13 -m venv .venv

# 3. 激活虚拟环境
source .venv/bin/activate

# 4. 安装依赖（activate 后直接用 pip）
pip install -r requirements.txt
pip install -e .

# 5. 启动服务（activate 后直接用 python）
python -m ascript_mcp.server

# 看到以下输出说明成功：
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 快速检查表

| 你想做什么 | activate 后的命令 | 不 activate 的命令 |
|-----------|-------------------|-------------------|
| 装依赖 | `pip install xxx` | `.venv/bin/pip install xxx` |
| 启动服务 | `python -m ascript_mcp.server` | `.venv/bin/python -m ascript_mcp.server` |
| 查看装了什么包 | `pip list` | `.venv/bin/pip list` |
| 确认 python 来源 | `which python` | - |

**记住一条：activate 之后，只用 `python` 和 `pip`，不要写完整的全局路径。**
