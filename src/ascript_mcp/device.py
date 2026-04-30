"""设备交互模块。

封装 Android / iOS 设备的 HTTP API 调用，
为本地 MCP 工具提供统一的设备操作接口。
"""

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Optional


# ------------------------------------------------------------------
# 设备数据模型
# ------------------------------------------------------------------

@dataclass
class Device:
    """已连接的设备。"""
    ip: str
    port: int = 9096
    platform: str = ""                # "android" / "ios"，connect 时自动探测
    password: str = ""
    name: str = ""
    connection_mode: str = "LocalIP"  # "LocalIP" / "ADB"
    serial: str = ""                  # ADB 序列号（仅 ADB 模式）
    _adb_api_port: int = 0            # ADB 转发的本地 API 端口
    _adb_ws_port: int = 0             # ADB 转发的本地 WS 端口
    _adb_debug_port: int = 0          # ADB 转发的本地 debugpy 端口（5678 被占时为 free port）

    @property
    def base_url(self) -> str:
        if self.connection_mode == "ADB" and self._adb_api_port:
            return f"http://127.0.0.1:{self._adb_api_port}"
        return f"http://{self.ip}:{self.port}"

    @property
    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.password:
            h["Cookie"] = f"airscript={self.password}"
        return h


# ------------------------------------------------------------------
# 设备状态管理（单进程，stdio 模式下只需要一个）
# ------------------------------------------------------------------

_current_device: Optional[Device] = None


def get_device() -> Optional[Device]:
    return _current_device


def set_device(device: Device) -> None:
    global _current_device
    _current_device = device


def require_device() -> Device:
    """获取当前设备，未连接时抛异常。ADB 设备自动确保端口转发有效。"""
    d = get_device()
    if d is None:
        raise RuntimeError("尚未连接设备。请先使用 connect_device 工具连接设备。")
    if d.connection_mode == "ADB":
        if not _ensure_adb_forward(d):
            raise RuntimeError(f"ADB 端口转发失败，设备 {d.serial} 可能已断开。")
    return d


# ------------------------------------------------------------------
# HTTP 工具
# ------------------------------------------------------------------

def _fetch_json(
    url: str,
    *,
    method: str = "POST",
    params: Optional[dict[str, str]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """发起请求并解析 JSON 响应。空 body 返回空 dict（兼容 iOS）。"""
    body = None
    if params:
        body = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8").strip()
        if not raw:
            return {}
        return json.loads(raw)


def _fetch_bytes(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    timeout: int = 15,
) -> bytes:
    """发起请求并返回原始字节。"""
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ------------------------------------------------------------------
# 连接 / 探测
# ------------------------------------------------------------------

def auto_connect_from_project(project_path: str) -> str:
    """
    从 AScript 工程目录的 .vscode/settings.json 读取设备信息并自动连接。
    对标 VSCode 插件：创建工程时会保存 ascript.platform 和 ascript.deviceId。

    连接失败时提供明确的下一步指引。
    """
    settings_path = os.path.join(project_path, ".vscode", "settings.json")
    if not os.path.isfile(settings_path):
        return (
            f"未找到 {settings_path}，当前目录可能不是 AScript 工程。\n"
            f"你可以：\n"
            f"- 使用 scan_devices 扫描局域网和 USB 设备\n"
            f"- 使用 connect_device 手动输入设备 IP 连接"
        )

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        return f"读取 settings.json 失败：{e}"

    platform = settings.get("ascript.platform", "")
    device_id = settings.get("ascript.deviceId", "")
    project_name = os.path.basename(project_path)

    if not device_id:
        if platform and platform.lower() == "windows":
            return f"当前工程 [{project_name}] 为 Windows 平台，脚本在本地运行，无需连接设备。"
        return (
            f"工程 [{project_name}] 的 settings.json 中没有 ascript.deviceId。\n"
            f"你可以：\n"
            f"- 使用 scan_devices 扫描设备后用 connect_device 连接\n"
            f"- 或在 VSCode 插件中重新选择设备"
        )

    # 解析 deviceId：格式为 "ip:port"（局域网）或 "usb_serial"（ADB）
    if device_id.startswith("usb_"):
        serial = device_id[4:]
        result = connect_adb(serial)
    else:
        parts = device_id.split(":")
        ip = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 9096
        result = connect(ip, port)

    if "失败" in result:
        # 连接失败，给出具体原因和下一步指引
        if device_id.startswith("usb_"):
            result += (
                f"\n\nADB 设备 [{device_id[4:]}] 连接失败，可能原因：\n"
                f"- USB 线已断开\n"
                f"- 设备上 AirScript 服务未启动\n"
                f"- ADB 授权已过期（请在设备上重新授权）\n\n"
            )
        else:
            result += (
                f"\n\n设备 [{device_id}] 连接失败，可能原因：\n"
                f"- 设备不在同一局域网或 IP 已变化\n"
                f"- 设备上 AirScript 服务未启动\n"
                f"- 设备已关机或休眠\n\n"
            )
        result += (
            f"你可以：\n"
            f"- 请用户确认设备状态后重试 auto_connect\n"
            f"- 使用 scan_devices 重新扫描设备\n"
            f"- 使用 connect_device 手动连接其他 {platform} 设备"
        )
        return result

    # 连接成功，校验平台是否匹配工程
    device = get_device()
    if device and platform:
        device_plat = device.platform.lower()     # "android" / "ios"
        project_plat = platform.lower()           # "Android" / "iOS" / "Ios"
        # 统一比较
        plat_map = {"android": "android", "ios": "ios", "Ios": "ios"}
        dp = plat_map.get(device_plat, device_plat)
        pp = plat_map.get(project_plat, project_plat)

        if dp != pp:
            set_device(None)  # 平台不匹配，断开
            return (
                f"平台不匹配！工程 [{project_name}] 是 {platform} 平台，"
                f"但设备 [{device_id}] 检测为 {device.platform}。\n\n"
                f"你可以：\n"
                f"- 使用 scan_devices 扫描设备，找到一台 {platform} 设备连接\n"
                f"- 使用 connect_device 手动连接一台 {platform} 设备\n"
                f"- 或请用户确认是否要切换工程平台"
            )

    result += f"\n工程名：{project_name}，平台：{platform}"
    return result


def connect(ip: str, port: int = 9096, password: str = "") -> str:
    """连接设备并自动探测平台类型，复用 _probe_platform 逻辑。"""
    device = Device(ip=ip, port=port, password=password)

    platform = _probe_platform(ip, port, password)
    if not platform:
        return f"连接失败：无法访问 {ip}:{port} 的 AirScript 服务，请确认设备已开启。"

    device.platform = platform
    device.name = f"{'Android' if platform == 'android' else 'iOS'} ({ip}:{port})"
    set_device(device)
    return f"已连接：{device.name}，平台：{device.platform}"


# ------------------------------------------------------------------
# 局域网扫描
# ------------------------------------------------------------------

def _get_local_prefixes() -> list[str]:
    """
    获取本机所有局域网 IPv4 前缀，如 ['192.168.1.', '10.0.0.']。
    1:1 对齐插件 getLocalIpPrefixes()：遍历所有网卡，排除 internal。
    """
    import psutil  # type: ignore

    prefixes: list[str] = []
    seen: set[str] = set()

    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        for iface_name, iface_addrs in addrs.items():
            # 跳过未启用的网卡
            if iface_name in stats and not stats[iface_name].isup:
                continue
            for addr in iface_addrs:
                if addr.family != socket.AF_INET:
                    continue
                ip = addr.address
                # 与插件一致：排除 internal（127.x），不额外过滤其他地址
                if not ip or ip.startswith("127."):
                    continue
                last_dot = ip.rfind(".")
                if last_dot > 0:
                    prefix = ip[: last_dot + 1]
                    if prefix not in seen:
                        seen.add(prefix)
                        prefixes.append(prefix)
    except ImportError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            prefix = ip[: ip.rfind(".") + 1]
            prefixes.append(prefix)
        except Exception:
            pass

    return prefixes


def _is_port_open(ip: str, port: int, timeout_s: float = 0.8) -> bool:
    """TCP 端口探测，对齐插件 isPortOpen。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_s)
        result = s.connect_ex((ip, port))
        s.close()
        return result == 0
    except Exception:
        return False


def _probe_platform(ip: str, port: int, password: str = "") -> Optional[str]:
    """
    探测设备平台，对齐插件 probeDevicePlatform。
    POST /api/model/pip:
      - code===1          → android
      - 其他有效响应/空体  → ios（iOS 该接口返回空 body 或 code!=1）
      - 网络/超时错误      → None（非 AScript 设备）
    """
    url = f"http://{ip}:{port}/api/model/pip"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if password:
        headers["Cookie"] = f"airscript={password}"
    try:
        req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8").strip()
            if not body:
                return "ios"  # iOS 返回空 body
            data = json.loads(body)
            return "android" if data.get("code") == 1 else "ios"
    except Exception:
        return None


def scan_devices(port: int = 9096) -> list[dict[str, Any]]:
    """
    局域网扫描，1:1 对齐插件 scanLocalDevices。

    流程：
    1. 合并所有子网 IP 列表（去重）
    2. 分批 80 并发端口扫描，每批等完才下一批
    3. 端口开放时立即异步提交平台探测（不阻塞当前批）
    4. 25s 总超时控制端口扫描批次
    5. 端口扫描全部完成后，统一等待所有平台探测结果
    """
    import time

    prefixes = _get_local_prefixes()
    if not prefixes:
        return []

    CONCURRENT = 80     # 与插件一致
    PROBE_MS = 0.8      # 800ms 单 IP 超时（与插件一致）
    TOTAL_S = 25.0      # 25s 总超时（与插件一致）

    # 合并所有子网的 IP 列表（去重），与插件完全一致
    ip_set: set[str] = set()
    for prefix in prefixes:
        for i in range(1, 255):
            ip_set.add(prefix + str(i))
    ips = list(ip_set)

    deadline = time.monotonic() + TOTAL_S

    # 端口开放时异步提交的平台探测 futures
    probe_pool = ThreadPoolExecutor(max_workers=20)
    probe_futures: list[tuple] = []  # (future, ip)

    try:
        # 分批端口扫描
        for batch_start in range(0, len(ips), CONCURRENT):
            if time.monotonic() > deadline:
                break

            batch = ips[batch_start: batch_start + CONCURRENT]

            # 当前批 80 并发端口扫描，等待全部完成
            with ThreadPoolExecutor(max_workers=CONCURRENT) as scan_pool:
                futures = {scan_pool.submit(_is_port_open, ip, port, PROBE_MS): ip for ip in batch}
                for future in as_completed(futures):
                    if future.result():
                        ip = futures[future]
                        # 端口开放 → 异步探测平台（不阻塞当前批）
                        pf = probe_pool.submit(_probe_platform, ip, port)
                        probe_futures.append((pf, ip))

        # 端口扫描完毕，统一等待所有平台探测完成（与插件 await Promise.all 一致）
        devices: list[dict[str, Any]] = []
        for pf, ip in probe_futures:
            try:
                platform = pf.result(timeout=10)
            except Exception:
                platform = None
            if platform:
                last_octet = ip.split(".")[-1]
                name = f"{'Android' if platform == 'android' else 'iOS'}-{last_octet}"
                devices.append({
                    "name": name,
                    "ip": ip,
                    "port": port,
                    "platform": platform,
                })
    finally:
        probe_pool.shutdown(wait=False)

    return devices


# ------------------------------------------------------------------
# ADB 设备扫描与端口转发
# ------------------------------------------------------------------

# adb 下载地址（与插件 adb.ts 一致，Google 官方）
_PLATFORM_TOOLS_URLS: dict[str, str] = {
    "win32": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
    "linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
}

# MCP 本地存储目录：~/.ascript-mcp/bin/
_MCP_BIN_DIR = os.path.join(os.path.expanduser("~"), ".ascript-mcp", "bin")

# 缓存已解析的 adb 路径
_resolved_adb: Optional[str] = None


def _find_executable_recursive(directory: str, name: str) -> Optional[str]:
    """在目录中递归查找可执行文件（与插件 findExecutable 对齐）。"""
    if not os.path.isdir(directory):
        return None
    direct = os.path.join(directory, name)
    if os.path.isfile(direct):
        return direct
    for entry in os.listdir(directory):
        full = os.path.join(directory, entry)
        if os.path.isdir(full) and entry not in ("__MACOSX", ".DS_Store"):
            found = _find_executable_recursive(full, name)
            if found:
                return found
    return None


def _download_platform_tools() -> Optional[str]:
    """
    下载 Google 官方 platform-tools 并解压到 ~/.ascript-mcp/bin/。
    与插件 adb.ts 的下载逻辑对齐。
    返回 adb 可执行文件路径，失败返回 None。
    """
    plat = sys.platform  # win32 / darwin / linux
    url = _PLATFORM_TOOLS_URLS.get(plat)
    if not url:
        return None

    exe = "adb.exe" if plat == "win32" else "adb"
    os.makedirs(_MCP_BIN_DIR, exist_ok=True)

    zip_path = os.path.join(_MCP_BIN_DIR, "platform-tools.zip")
    try:
        # 下载
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)

        # 解压
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(_MCP_BIN_DIR)

        # 清理 zip
        try:
            os.unlink(zip_path)
        except Exception:
            pass

        # 查找解压后的 adb
        found = _find_executable_recursive(_MCP_BIN_DIR, exe)
        if found and plat != "win32":
            os.chmod(found, 0o755)
        return found

    except Exception:
        # 清理失败的下载
        try:
            os.unlink(zip_path)
        except Exception:
            pass
        return None


def _find_adb() -> Optional[str]:
    """
    查找 adb 可执行文件路径。与插件 adb.ts 对齐：
    1. 已缓存的路径
    2. ~/.ascript-mcp/bin/ 下已下载的
    3. ANDROID_HOME/platform-tools
    4. PATH 中的 adb
    5. 都没有则自动下载
    """
    global _resolved_adb
    exe = "adb.exe" if os.name == "nt" else "adb"

    # 0. 缓存
    if _resolved_adb and os.path.isfile(_resolved_adb):
        return _resolved_adb

    # 1. MCP 本地 bin 目录（之前下载过的）
    found = _find_executable_recursive(_MCP_BIN_DIR, exe)
    if found:
        _resolved_adb = found
        return found

    # 2. ANDROID_HOME / ANDROID_SDK_ROOT
    for env_key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        android_home = os.environ.get(env_key)
        if android_home:
            p = os.path.join(android_home, "platform-tools", exe)
            if os.path.isfile(p):
                _resolved_adb = p
                return p

    # 3. PATH
    from_path = shutil.which("adb")
    if from_path:
        _resolved_adb = from_path
        return from_path

    # 4. 自动下载
    downloaded = _download_platform_tools()
    if downloaded:
        _resolved_adb = downloaded
        return downloaded

    return None


def scan_adb_devices() -> list[dict[str, Any]]:
    """
    通过 adb devices 扫描 USB 连接的 Android 设备。
    与插件 scanAdbDevices 对齐。
    """
    adb = _find_adb()
    if not adb:
        return []

    try:
        result = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
    except Exception:
        return []

    devices: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("List"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip().lower() == "device":
            serial = parts[0].strip()
            devices.append({
                "name": f"ADB {serial}",
                "ip": serial,  # ADB 设备 ip 字段存序列号
                "port": 9096,
                "platform": "android",
                "connection_mode": "ADB",
            })

    return devices


def _find_free_port() -> int:
    """查找系统空闲端口。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _adb_forward(adb: str, serial: str, local_port: int, remote_port: int) -> bool:
    """执行 adb forward，将本地端口映射到设备端口。"""
    try:
        result = subprocess.run(
            [adb, "-s", serial, "forward", f"tcp:{local_port}", f"tcp:{remote_port}"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _ensure_adb_forward(device: Device) -> bool:
    """
    确保 ADB 设备的端口转发已建立。
    与插件 ensureAdbForward 对齐：转发 API(9096) 和 WS(10102) 两个端口。
    """
    if device.connection_mode != "ADB":
        return True
    if device._adb_api_port:
        # 已建立转发，检查是否仍有效
        if _is_port_open("127.0.0.1", device._adb_api_port, 1.0):
            return True

    adb = _find_adb()
    if not adb:
        return False

    serial = device.serial or device.ip
    api_port = _find_free_port()
    ws_port = _find_free_port()

    api_ok = _adb_forward(adb, serial, api_port, 9096)
    ws_ok = _adb_forward(adb, serial, ws_port, 10102)

    if not api_ok or not ws_ok:
        return False

    device._adb_api_port = api_port
    device._adb_ws_port = ws_port
    return True


# ------------------------------------------------------------------
# 连接（更新，支持 ADB）
# ------------------------------------------------------------------

def connect_adb(serial: str) -> str:
    """连接 ADB 设备：建立端口转发，探测平台。"""
    device = Device(
        ip=serial,
        port=9096,
        platform="android",
        connection_mode="ADB",
        serial=serial,
    )

    if not _ensure_adb_forward(device):
        return f"ADB 端口转发失败，请确认设备 {serial} 已通过 USB 连接。"

    # 探测平台确认
    platform = _probe_platform("127.0.0.1", device._adb_api_port)
    if not platform:
        return f"设备 {serial} 端口转发成功但无法访问 AirScript 服务，请确认 App 已启动。"

    device.platform = platform
    device.name = f"ADB {serial} ({platform})"
    set_device(device)
    return f"已连接：{device.name}（通过 ADB，本地端口 {device._adb_api_port}）"


# ------------------------------------------------------------------
# 截图
# ------------------------------------------------------------------

def screen_capture() -> dict[str, Any]:
    """截取设备屏幕，返回 base64 编码的 PNG 图片。"""
    d = require_device()
    if d.platform == "android":
        url = f"{d.base_url}/api/tool/screen/capture"
    else:
        url = f"{d.base_url}/api/screen/capture"

    data = _fetch_bytes(url, headers=d.headers, timeout=10)
    b64 = base64.b64encode(data).decode("ascii")
    return {
        "format": "png",
        "base64": b64,
        "size_bytes": len(data),
    }


# ------------------------------------------------------------------
# 控件树
# ------------------------------------------------------------------

_VIEW_MODES = {
    0: "普通模式（重要控件）",
    1: "复杂模式（所有控件，层级深）",
    2: "简单模式（过滤系统控件）",
    3: "复杂模式（过滤系统控件）",
    6: "Hid 控件模式",
    9: "Root 模式",
}


def dump_ui_tree(mode: int = 0, selector: str = "") -> dict[str, Any] | str:
    """
    获取设备当前界面的控件树。

    Android mode: 0=普通, 1=复杂, 2=简单过滤系统, 3=复杂过滤系统, 6=Hid, 9=Root
    Android 返回 JSON，iOS 返回 XML（WDA 格式）。
    """
    d = require_device()

    if d.platform == "android":
        params: dict[str, str] = {"mode": str(mode)}
        if selector:
            params["selector"] = selector
        url = f"{d.base_url}/api/tool/view/dump?" + urllib.parse.urlencode(params)
        return _fetch_json(url, method="GET", headers=d.headers)
    else:
        url = f"{d.base_url}/api/node/dump"
        xml_data = _fetch_bytes(url, headers=d.headers, timeout=15)
        return xml_data.decode("utf-8")


# ------------------------------------------------------------------
# 测试 Selector
# ------------------------------------------------------------------

def test_selector(
    text: Optional[str] = None,
    id: Optional[str] = None,
    type: Optional[str] = None,
    desc: Optional[str] = None,
    clickable: Optional[bool] = None,
    mode: int = 0,
) -> dict[str, Any] | str:
    """
    在设备上实时测试 Selector 选择器，返回匹配到的控件列表。
    用于验证选择器是否能精准定位到目标控件。

    参数即 Selector 的过滤条件，可组合使用。
    Android 返回匹配控件的完整属性（id、text、type、rect、clickable 等）。
    """
    d = require_device()

    # 构建 selector JSON（与 Android SelectorProxy 格式对齐）
    link: list[dict] = []
    if text is not None:
        link.append({"key": "text", "value": [text]})
    if id is not None:
        link.append({"key": "id", "value": [id]})
    if type is not None:
        link.append({"key": "type", "value": [type]})
    if desc is not None:
        link.append({"key": "desc", "value": [desc]})
    if clickable is not None:
        link.append({"key": "clickable", "value": [clickable]})

    if not link:
        return {"error": "至少需要提供一个过滤条件（text/id/type/desc/clickable）"}

    selector = json.dumps({
        "sels": [{"link": link}],
        "mode": mode,
        "find": 1,  # 1=查找所有匹配
    })

    if d.platform == "android":
        params = {"selector": selector, "mode": str(mode)}
        url = f"{d.base_url}/api/tool/view/dump?" + urllib.parse.urlencode(params)
        return _fetch_json(url, method="GET", headers=d.headers)
    else:
        url = f"{d.base_url}/api/node/dump"
        xml_data = _fetch_bytes(url, headers=d.headers, timeout=15)
        return xml_data.decode("utf-8")


# ------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------

_OCR_MODES = {
    "mlkit": 1,
    "paddle_v2": 2,
    "paddle_v3": 3,
    "tess": 4,
}


def ocr(
    mode: str = "mlkit",
    rect: Optional[list[int]] = None,
    pattern: Optional[str] = None,
    confidence: float = 0.1,
) -> dict[str, Any]:
    """
    在设备屏幕上执行 OCR 文字识别。

    mode: mlkit / paddle_v2 / paddle_v3 / tess
    rect: [left, top, right, bottom] 识别区域，不传则全屏
    pattern: 正则过滤
    confidence: 置信度阈值 0.0-1.0
    """
    d = require_device()
    mode_int = _OCR_MODES.get(mode, 1)

    # 构建 GP strack 参数
    params_parts = [f"mode={mode_int}"]
    if rect:
        params_parts.append(f"rect={rect}")
    if pattern:
        params_parts.append(f"pattern='{pattern}'")
    params_parts.append(f"confidence={confidence}")
    params_str = ", ".join(params_parts)

    return _run_gp(d, "ascript.android.screen.Ocr" if d.platform == "android" else "ascript.ios.screen.Ocr", params_str)


# ------------------------------------------------------------------
# 找色
# ------------------------------------------------------------------

def find_colors(
    colors: str,
    rect: Optional[list[int]] = None,
    diff: float = 0.98,
    space: int = 5,
    ori: int = 2,
) -> dict[str, Any]:
    """
    多点找色。

    colors: 颜色描述字符串，格式 "x,y,#RRGGBB|x,y,#RRGGBB|..."
    rect: [left, top, right, bottom] 搜索区域
    diff: 相似度 0.0-1.0
    space: 间距
    ori: 搜索方向 1-8
    """
    d = require_device()
    params_parts = [f"colors='{colors}'"]
    if rect:
        params_parts.append(f"rect={rect}")
    params_parts.append(f"diff={diff}")
    params_parts.append(f"space={space}")
    params_parts.append(f"ori={ori}")
    params_str = ", ".join(params_parts)

    cls = "ascript.android.screen.FindColors" if d.platform == "android" else "ascript.ios.screen.FindColors"
    return _run_gp(d, cls, params_str)


# ------------------------------------------------------------------
# 比色
# ------------------------------------------------------------------

def compare_colors(colors: str, diff: float = 0.9) -> dict[str, Any]:
    """
    多点比色。

    colors: 颜色描述字符串，格式 "x,y,#RRGGBB|x,y,#RRGGBB|..."
    diff: 相似度阈值 0.0-1.0
    """
    d = require_device()
    params_str = f"colors='{colors}', diff={diff}"
    cls = "ascript.android.screen.CompareColors" if d.platform == "android" else "ascript.ios.screen.CompareColors"
    return _run_gp(d, cls, params_str)


# ------------------------------------------------------------------
# GP 执行引擎
# ------------------------------------------------------------------

def _ensure_screenshot(device: Device) -> str:
    """
    在设备端截图并保存，返回设备上的截图文件路径。
    GP 引擎需要一个设备端的图片路径才能工作。
    """
    if device.platform == "android":
        # 用 path 参数指定保存路径，GP 引擎从该路径读取
        save_path = "/sdcard/airscript/screen/mcp_temp.png"
        url = f"{device.base_url}/api/tool/screen/capture?path={urllib.parse.quote(save_path)}"
        _fetch_bytes(url, headers=device.headers, timeout=10)
        return save_path
    else:
        # iOS: /api/screen/capture/list?capture=true 截图并保存到设备，返回路径
        url = f"{device.base_url}/api/screen/capture/list?capture=true"
        result = _fetch_json(url, method="GET", headers=device.headers, timeout=10)
        items = result.get("data", [])
        if items:
            return items[-1].get("path", "")
        return ""


def _run_gp(device: Device, class_id: str, params_str: str) -> dict[str, Any]:
    """
    调用设备 GP 引擎执行图色工具。

    流程：1) 先在设备端截图保存  2) 用截图路径调 GP strack 引擎
    通过 /api/gp/strack (Android) 或 /api/screen/gp (iOS) 发送请求。
    """
    # 先截图保存到设备
    image_path = _ensure_screenshot(device)

    strack = [
        {
            "id": class_id,
            "type": "图色工具",
            "data": {"params": params_str},
        }
    ]

    if device.platform == "android":
        url = f"{device.base_url}/api/gp/strack"
    else:
        url = f"{device.base_url}/api/screen/gp"

    payload = {
        "strack": json.dumps(strack),
        "image": image_path,
        "gp": "as_gp_test_screen_temp",
    }
    body = urllib.parse.urlencode(payload).encode("utf-8")
    headers = dict(device.headers)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ------------------------------------------------------------------
# 工程管理
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 组合工具（减少调用轮次，加速开发循环）
# ------------------------------------------------------------------

def observe_device() -> dict[str, Any]:
    """
    一次性获取设备当前状态：截图 + 控件树。
    替代分别调用 screen_capture 和 dump_ui_tree，减少一次往返。
    """
    d = require_device()

    # 截图
    if d.platform == "android":
        img_url = f"{d.base_url}/api/tool/screen/capture"
    else:
        img_url = f"{d.base_url}/api/screen/capture"
    img_data = _fetch_bytes(img_url, headers=d.headers, timeout=10)
    b64 = base64.b64encode(img_data).decode("ascii")

    # 控件树
    if d.platform == "android":
        tree_url = f"{d.base_url}/api/tool/view/dump?" + urllib.parse.urlencode({"mode": "2"})
        tree = _fetch_json(tree_url, method="GET", headers=d.headers)
    else:
        tree_url = f"{d.base_url}/api/node/dump"
        xml_data = _fetch_bytes(tree_url, headers=d.headers, timeout=15)
        tree = xml_data.decode("utf-8")

    return {
        "screenshot": {"format": "png", "base64": b64, "size_bytes": len(img_data)},
        "ui_tree": tree,
    }


def deploy_and_run(
    project_name: str,
    code: str,
    log_seconds: float = 5.0,
) -> dict[str, Any]:
    """
    一步完成：上传代码 → 运行 → 收集日志 → 截图验证。
    替代分别调用 upload_file + run_project + get_run_log + screen_capture。
    """
    import time as _time
    d = require_device()

    # 1. 上传
    upload_result = upload_file(project_name, "__init__.py", code.encode("utf-8"))

    # 2. 运行
    run_result = run_project(project_name)

    # 3. 收集日志（WebSocket 连接本身就会等待 log_seconds 秒）
    logs = get_run_log(seconds=log_seconds)

    # 4. 截图
    if d.platform == "android":
        img_url = f"{d.base_url}/api/tool/screen/capture"
    else:
        img_url = f"{d.base_url}/api/screen/capture"
    img_data = _fetch_bytes(img_url, headers=d.headers, timeout=10)
    b64 = base64.b64encode(img_data).decode("ascii")

    # 格式化日志
    log_lines = []
    for log in logs:
        tag = {"e": "ERROR", "o": "OUT", "i": "INFO"}.get(log.get("type", ""), "LOG")
        log_lines.append(f"[{tag}] {log.get('time', '')} {log.get('msg', '')}")

    return {
        "upload": upload_result,
        "run": run_result,
        "logs": "\n".join(log_lines) if log_lines else "(未收集到日志)",
        "screenshot": {"format": "png", "base64": b64, "size_bytes": len(img_data)},
    }


def create_project(name: str) -> dict[str, Any]:
    """在设备上创建工程。"""
    d = require_device()
    if d.platform == "android":
        url = f"{d.base_url}/api/model/create"
        return _fetch_json(url, method="POST", params={"name": name}, headers=d.headers)
    else:
        url = f"{d.base_url}/api/module/create?" + urllib.parse.urlencode({"name": name})
        return _fetch_json(url, method="GET", headers=d.headers)


def list_projects() -> dict[str, Any]:
    """列出设备上的工程。"""
    d = require_device()
    if d.platform == "android":
        url = f"{d.base_url}/api/model/getlist"
    else:
        url = f"{d.base_url}/api/module/list"
    return _fetch_json(url, method="POST", headers=d.headers)


def run_project(name: str) -> dict[str, Any]:
    """在设备上运行指定工程。"""
    d = require_device()
    if d.platform == "android":
        url = f"{d.base_url}/api/model/run"
        return _fetch_json(url, method="POST", params={"name": name}, headers=d.headers)
    else:
        url = f"{d.base_url}/api/module/run?" + urllib.parse.urlencode({"name": name})
        return _fetch_json(url, method="GET", headers=d.headers)


def get_run_log(seconds: float = 3.0) -> list[dict[str, Any]]:
    """
    获取设备运行日志。连接 WebSocket 收集指定秒数的日志后返回。
    日志格式：{type: 'e'(错误)/'o'(输出)/'i'(信息), msg: str, time: str}
    """
    import threading
    import time as _time

    d = require_device()

    if d.connection_mode == "ADB" and d._adb_ws_port:
        ws_host, ws_port = "127.0.0.1", d._adb_ws_port
    else:
        ws_host, ws_port = d.ip, 10102

    logs: list[dict[str, Any]] = []
    done = threading.Event()

    def _collect():
        import struct
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(seconds + 2)
        try:
            s.connect((ws_host, ws_port))
            # WebSocket 握手
            key = base64.b64encode(os.urandom(16)).decode()
            cookie = f"airscript={d.password}" if d.password else ""
            handshake = (
                f"GET /log/ HTTP/1.1\r\n"
                f"Host: {ws_host}:{ws_port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
            )
            if cookie:
                handshake += f"Cookie: {cookie}\r\n"
            handshake += "\r\n"
            s.sendall(handshake.encode())

            # 读取握手响应
            resp = b""
            while b"\r\n\r\n" not in resp:
                chunk = s.recv(4096)
                if not chunk:
                    return
                resp += chunk

            # 收集日志帧
            deadline = _time.monotonic() + seconds
            buf = b""
            while _time.monotonic() < deadline and not done.is_set():
                try:
                    data = s.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                buf += data
                # 解析 WebSocket 帧
                while len(buf) >= 2:
                    opcode = buf[0] & 0x0F
                    masked = (buf[1] & 0x80) != 0
                    payload_len = buf[1] & 0x7F
                    offset = 2
                    if payload_len == 126:
                        if len(buf) < 4:
                            break
                        payload_len = struct.unpack(">H", buf[2:4])[0]
                        offset = 4
                    elif payload_len == 127:
                        if len(buf) < 10:
                            break
                        payload_len = struct.unpack(">Q", buf[2:10])[0]
                        offset = 10
                    if masked:
                        offset += 4
                    if len(buf) < offset + payload_len:
                        break
                    if masked:
                        mask_key = buf[offset - 4: offset]
                        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(buf[offset: offset + payload_len]))
                    else:
                        payload = buf[offset: offset + payload_len]
                    buf = buf[offset + payload_len:]

                    if opcode == 0x01:  # text frame
                        try:
                            msg = json.loads(payload.decode("utf-8"))
                            logs.append(msg)
                        except Exception:
                            logs.append({"type": "o", "msg": payload.decode("utf-8", errors="replace"), "time": ""})
                    elif opcode == 0x09:  # ping
                        # 回 pong
                        pong = bytes([0x8A, len(payload)]) + payload
                        try:
                            s.sendall(pong)
                        except Exception:
                            pass
                    elif opcode == 0x08:  # close
                        return
        except Exception:
            pass
        finally:
            try:
                s.close()
            except Exception:
                pass

    t = threading.Thread(target=_collect, daemon=True)
    t.start()
    t.join(timeout=seconds + 3)
    done.set()
    return logs


def stop_project() -> dict[str, Any]:
    """停止设备上正在运行的工程。"""
    d = require_device()
    if d.platform == "android":
        url = f"{d.base_url}/api/model/stop"
        return _fetch_json(url, method="POST", headers=d.headers, timeout=5)
    else:
        url = f"{d.base_url}/api/module/stop"
        return _fetch_json(url, method="GET", headers=d.headers, timeout=5)


# ------------------------------------------------------------------
# 已安装 Python 包清单（Android: /api/status.python.packages，iOS: eval importlib.metadata）
# ------------------------------------------------------------------

# iOS 走 eval_python + importlib.metadata 列出实际安装包；Android 直接复用 /api/status
_IOS_LIST_PACKAGES_CODE = (
    "import importlib.metadata as _md, json\n"
    "_pkgs = sorted({f\"{d.metadata['Name']}=={d.version}\" "
    "for d in _md.distributions() if d.metadata.get('Name')})\n"
    "_result = json.dumps({'install': list(_pkgs)})\n"
)

def list_python_packages() -> dict[str, Any]:
    """获取设备 AScript App 内已安装的 Python 第三方库清单（Android + iOS）。

    AI 写代码（特别是 eval_python 片段）前调用，确认要用的 lib 是否可用，
    避免写出 `import xxx` 但设备上不存在导致运行时炸。

    Android: 调 /api/status 取 python.packages（importlib.metadata 实时查询）。
    iOS:     通过 eval_python 跑 importlib.metadata 列出实际安装包。

    返回 dict：
      {
        "packages": ["opencv-python-headless==4.5.1.48", "numpy==1.26.0", ...],
        "count": 13,
        "source": "android-importlib-metadata" | "ios-importlib-metadata",
      }
    """
    d = require_device()

    if d.platform == "android":
        status = get_device_status()
        pkgs_dict = (status.get("python") or {}).get("packages") or {}
        packages = sorted(f"{name}=={ver}" for name, ver in pkgs_dict.items())
        return {
            "packages": packages,
            "count": len(packages),
            "source": "android-importlib-metadata",
        }

    if d.platform == "ios":
        evalres = eval_python(_IOS_LIST_PACKAGES_CODE)
        if evalres.get("_format") == "json":
            data = evalres.get("data") or {}
            packages = data.get("install") or [] if isinstance(data, dict) else []
            return {
                "packages": packages,
                "count": len(packages),
                "source": "ios-importlib-metadata",
            }
        return {
            "error": f"iOS 包列表查询失败：{evalres.get('error', '未知错误')}",
            "packages": [],
            "count": 0,
            "source": "ios-importlib-metadata",
        }

    return {"error": f"平台 {d.platform} 不支持。", "packages": [], "count": 0}


# ------------------------------------------------------------------
# 设备 Python REPL（/api/gp/eval 直接 exec 任意代码，Android + iOS）
# ------------------------------------------------------------------

# eval 返回值大小上限：避免 AI 误用（截屏 / 大文件 read）撑爆 MCP 对话上下文
_EVAL_MAX_IMAGE_B64 = 2 * 1024 * 1024   # 2MB base64 ≈ 1.5MB raw PNG
_EVAL_MAX_TEXT = 256 * 1024             # 256KB 纯文本


def _truncate(s: str, limit: int) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n...[truncated, total={len(s)} chars > limit={limit}]"

def eval_python(code: str, image_path: str = "") -> dict[str, Any]:
    """在设备主进程的 Python 上下文中执行任意代码，返回 _result 全局变量。

    Android 与 iOS 都支持。iOS 端会自动将 `ascript.android.` 替换为 `ascript.ios.`，
    并预加载 cv2 / np / Image（PIL）到执行环境，跨平台片段几乎无需修改。

    与 run_project 的区别：
      - eval_python 在 App 主进程（请求级 fresh globals）里跑，不需要工程，
        立即返回结果，几百毫秒一轮，适合探索/调试/复合决策
      - run_project 在 :py 子进程跑工程代码，需要 upload_file，适合长跑脚本

    AI 用法约定（写 code 时遵循）：
      ```python
      # 1. 简单字符串：
      _result = "ok"

      # 2. 结构化数据（推荐）：
      import json
      _result = json.dumps({"found": True, "x": 320, "y": 800})

      # 3. 含截图返回：
      import json, base64, io
      buf = io.BytesIO(); cropped.save(buf, "PNG")
      _result = json.dumps({
          "data": {...},
          "image_base64": base64.b64encode(buf.getvalue()).decode(),
      })
      ```

    image_path 非空时 App 端会注入 `_im_source = '<image_path>'` 全局变量
    （沿用现有 GP 工具约定，让代码读取已有图片而非重新 capture）。
    iOS 上若代码引用 `img` 变量，且 image_path 指向的文件存在，会被预读为 cv2 ndarray。

    返回 dict（MCP 层智能解析）：
      - {"_format": "image", "image_base64": ..., "data": ...}  含图，含其他字段
      - {"_format": "json", "data": <parsed>}                   纯结构化数据
      - {"_format": "text", "data": "<raw>"}                    非 JSON 字符串
      - {"_format": "error", "error": "...", "code": ...}       服务端报错
    """
    d = require_device()
    url = f"{d.base_url}/api/gp/eval"
    res = _fetch_json(
        url,
        method="POST",
        params={"code": code, "image": image_path or ""},
        headers=d.headers,
        timeout=60,
    )
    if res.get("code") != 1:
        return {
            "_format": "error",
            "error": res.get("msg") or "eval 失败",
            "code": res.get("code"),
        }

    raw = res.get("data", "")
    if raw is None:
        raw = ""
    raw = str(raw).strip()
    if raw == "" or raw == "null":
        return {"_format": "text", "data": ""}

    # 智能解析：JSON 失败回退原文。截断超大文本避免炸 MCP 上下文。
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {"_format": "text", "data": _truncate(raw, _EVAL_MAX_TEXT)}

    # 含 image_base64 字段则拆出来作为多模态返回；超 cap 则丢图保留警告
    if isinstance(parsed, dict) and parsed.get("image_base64"):
        img_b64 = parsed.pop("image_base64")
        if len(img_b64) > _EVAL_MAX_IMAGE_B64:
            parsed["_warning"] = (
                f"image_base64 太大（{len(img_b64)} 字节）已丢弃。"
                "请在代码里压缩或裁剪后再返回（建议 PNG ≤1.5MB / base64 ≤2MB）。"
            )
            return {"_format": "json", "data": parsed}
        return {"_format": "image", "image_base64": img_b64, "data": parsed}

    return {"_format": "json", "data": parsed}


# ------------------------------------------------------------------
# 设备运行状态（Android only — /api/status 一次性返回 device/system/screen/battery/
#   network/storage/memory/permissions/app/python/run_mode/runtime/tools 全集）
# ------------------------------------------------------------------

def get_device_status() -> dict[str, Any]:
    """获取设备完整运行状态（Android）。

    返回 dict 包含：
      device     设备品牌/型号/ABI
      system     Android 版本/SDK/语言/时区
      screen     分辨率/dpi/方向
      battery    电量/充电状态/温度
      network    联网类型/IP
      storage    存储总量/可用
      memory     运行内存
      permissions 全部权限的授权状态（运行时 + 设置类）
      app        AScript App 版本/包名
      run_mode   运行模式：root / accessibility / screen_only / hid
      runtime    is_script_running 与正在跑的工程信息
      tools      已安装工具配置

    AI 在生成脚本前应先调用此工具，根据 run_mode、permissions、screen 等
    适配代码（不同模式下可用 API 不同），并避开正在跑的脚本。
    """
    d = require_device()
    if d.platform != "android":
        return {"error": "/api/status 仅 Android 平台提供。"}
    url = f"{d.base_url}/api/status"
    res = _fetch_json(url, method="POST", headers=d.headers, timeout=10)
    if res.get("code") != 1:
        return {"error": res.get("msg") or "device API 报错", "code": res.get("code")}
    return res.get("data") or {}


# ------------------------------------------------------------------
# debugpy 调试支持（Android only，复用 ADB 端口转发）
# ------------------------------------------------------------------

DEBUGPY_PORT = 5678


def _ensure_debug_forward(device: Device) -> int:
    """为 debugpy 建立 adb forward；优先 5678→5678，被占则取 free port→5678。

    返回本地端口；失败返回 0。仅 ADB 模式。
    缓存到 device._adb_debug_port，重复调用复用同一端口避免 forward 泄漏。
    """
    if device.connection_mode != "ADB":
        return 0

    # 已有缓存且仍可用 → 复用
    if device._adb_debug_port and _is_port_open("127.0.0.1", device._adb_debug_port, 0.3):
        return device._adb_debug_port

    adb = _find_adb()
    if not adb:
        return 0
    serial = device.serial or device.ip

    local_port = DEBUGPY_PORT
    if _is_port_open("127.0.0.1", local_port, 0.3):
        # 5678 被别的进程占了（不是自家 forward — 那条会走上面的 cache 复用），取 free port
        local_port = _find_free_port()

    if not _adb_forward(adb, serial, local_port, DEBUGPY_PORT):
        return 0

    device._adb_debug_port = local_port
    return local_port


def run_project_debug(name: str) -> dict[str, Any]:
    """以调试模式启动 Android 工程，自动建立 adb forward 并返回 attach 信息。

    流程：
      1. 校验：必须 Android + ADB 连接（debugpy 监听设备 127.0.0.1:5678，
         LAN 模式无法穿透）。
      2. adb forward tcp:<local_port> tcp:5678（local 优先 5678）。
      3. POST /api/model/run?name=<name>&debug=1 让 :py 进入
         start_for_debug(wait=True) 阻塞等 IDE attach。
      4. 立即返回端口与 launch.json 片段；用户在 VS Code 创建 attach
         配置（host=localhost, port=local_port）attach 后业务自动开跑。
    """
    d = require_device()
    if d.platform != "android":
        return {
            "success": False,
            "error": "调试模式仅支持 Android（iOS 暂未集成 debugpy）。",
        }
    if d.connection_mode != "ADB":
        return {
            "success": False,
            "error": (
                "调试模式需要 ADB 连接：debugpy 监听设备 127.0.0.1:5678，"
                "局域网无法穿透。请用 USB 连上后通过 connect_device(serial) "
                "或 scan_devices 重新连接。"
            ),
        }

    local_port = _ensure_debug_forward(d)
    if not local_port:
        return {
            "success": False,
            "error": (
                f"adb forward tcp:5678 失败。请确认 USB 连接正常，"
                f"或手动执行 `adb -s {d.serial or d.ip} forward tcp:5678 tcp:5678`。"
            ),
        }

    url = f"{d.base_url}/api/model/run"
    res = _fetch_json(
        url, method="POST", params={"name": name, "debug": "1"}, headers=d.headers
    )
    if res.get("code") != 1:
        return {
            "success": False,
            "error": res.get("msg") or "设备启动调试失败（/api/model/run 返回非 1）",
            "device_run_response": res,
        }

    launch_snippet = json.dumps(
        {
            "name": f"AScript: attach to {name}",
            "type": "debugpy",
            "request": "attach",
            "connect": {"host": "localhost", "port": local_port},
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": ".",
                }
            ],
            "justMyCode": False,
        },
        ensure_ascii=False,
        indent=2,
    )

    return {
        "success": True,
        "device_run_response": res,
        "local_port": local_port,
        "remote_port": DEBUGPY_PORT,
        "host": "localhost",
        "launch_json": launch_snippet,
        "hint": (
            f"调试服务已在设备启动并阻塞等待 attach。\n"
            f"在 VS Code / Cursor 的 .vscode/launch.json 里加入下方配置后按 F5 attach；"
            f"attach 成功后业务从 main 开始运行，断点会被命中。\n"
            f"停止调试请调用 stop_project（同时停止业务和调试器）。"
        ),
    }


# ------------------------------------------------------------------
# 文件操作
# ------------------------------------------------------------------

def get_project_files(name: str) -> dict[str, Any]:
    """获取设备上指定工程的文件树。"""
    d = require_device()
    if d.platform == "android":
        url = f"{d.base_url}/api/model/get"
        return _fetch_json(url, method="POST", params={"name": name}, headers=d.headers)
    else:
        url = f"{d.base_url}/api/module/files?" + urllib.parse.urlencode({"name": name})
        return _fetch_json(url, method="GET", headers=d.headers)


def _ensure_project(device: Device, project_name: str) -> None:
    """
    确保设备上工程已存在，对标插件 pullProjectFromDevice 逻辑：
    先 create，已存在则忽略错误继续。create 后短暂等待让设备生成默认文件。
    """
    import time as _time
    try:
        if device.platform == "android":
            url = f"{device.base_url}/api/model/create"
            result = _fetch_json(url, method="POST", params={"name": project_name}, headers=device.headers)
        else:
            url = f"{device.base_url}/api/module/create?" + urllib.parse.urlencode({"name": project_name})
            result = _fetch_json(url, method="GET", headers=device.headers)

        # create 成功或已存在都继续
        code = result.get("code")
        msg = result.get("msg", "") or result.get("message", "") or ""
        if code != 1 and "已存在" not in msg and "exists" not in msg.lower():
            # 真正的错误
            pass
        # 与插件一致：create 后短暂等待让设备生成默认文件
        _time.sleep(0.6)
    except Exception:
        pass  # 网络错误等忽略，后续上传会报更明确的错


def upload_file(project_name: str, relative_path: str, content: bytes) -> dict[str, Any]:
    """
    上传文件到设备上的指定工程。
    对标插件逻辑：上传前自动确保工程存在（不存在则创建，已存在则忽略）。
    """
    d = require_device()

    # 确保工程存在（对标插件 pullProjectFromDevice 中的 create 逻辑）
    _ensure_project(d, project_name)

    boundary = f"----AScriptMCP{id(content)}"
    line = "\r\n"

    if d.platform == "android":
        remote_root = f"/storage/emulated/0/airscript/model/{project_name}/"
        target_encoded = urllib.parse.quote(remote_root)

        part1 = (
            f"--{boundary}{line}"
            f'Content-Disposition: form-data; name="targetPath"{line}{line}'
            f"{target_encoded}{line}"
        ).encode("utf-8")
        part2 = (
            f"--{boundary}{line}"
            f'Content-Disposition: form-data; name="files"; filename="{urllib.parse.quote(relative_path)}"{line}'
            f"Content-Type: application/octet-stream{line}{line}"
        ).encode("utf-8")
        part3 = f"{line}--{boundary}--{line}".encode("utf-8")
        body = part1 + part2 + content + part3
        url = f"{d.base_url}/api/file/upload2"
    else:
        full_path = f"~/modules/{project_name}/{relative_path}"
        path_param = urllib.parse.quote(full_path)
        file_name = relative_path.rsplit("/", 1)[-1]

        part1 = (
            f"--{boundary}{line}"
            f'Content-Disposition: form-data; name="files"; filename="{urllib.parse.quote(file_name)}"{line}'
            f"Content-Type: application/octet-stream{line}{line}"
        ).encode("utf-8")
        part2 = f"{line}--{boundary}--{line}".encode("utf-8")
        body = part1 + content + part2
        url = f"{d.base_url}/api/file/upload?path={path_param}&overwrite=true"

    headers = dict(d.headers)
    headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(remote_path: str) -> bytes:
    """从设备下载文件，返回字节内容。"""
    d = require_device()
    path_param = urllib.parse.quote(remote_path)
    if d.platform == "android":
        url = f"{d.base_url}/api/file/download?path={path_param}"
    else:
        url = f"{d.base_url}/api/file/get?path={path_param}"
    return _fetch_bytes(url, headers=d.headers, timeout=30)


# ------------------------------------------------------------------
# Web 控件 (Android)
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 在线插件查询
# ------------------------------------------------------------------

_PLUG_LIST_URL = "https://py.airscript.cn/api/web/plug/list?limit=10000"
_PLUG_DETAIL_URL = "https://py.airscript.cn/api/web/plug/versionList?id={id}"


def list_plugins() -> str:
    """查询 AScript 在线插件库，返回所有可用插件列表。"""
    try:
        result = _fetch_json(_PLUG_LIST_URL, method="GET", timeout=10)
    except Exception as e:
        return f"查询插件列表失败：{e}"

    plugins = result.get("data", [])
    if not plugins:
        return "插件库为空。"

    lines = [f"共 {len(plugins)} 个插件：\n"]
    # 按下载量排序
    plugins.sort(key=lambda p: p.get("download", 0), reverse=True)
    for p in plugins:
        name = p.get("name", "")
        author = p.get("auth", "")
        desc = p.get("desc", "")
        downloads = p.get("download", 0)
        pid = p.get("id", "")
        lines.append(f"- **{name}** (id={pid}) by {author} | {downloads}次使用")
        if desc:
            lines.append(f"  {desc}")
    lines.append("\n使用 get_plugin_detail 查看插件详细文档和 API。")
    lines.append("使用方式：plug.load(\"插件名:版本号\")")
    return "\n".join(lines)


def get_plugin_detail(plugin_id: int) -> str:
    """获取指定插件的详细文档，包括 API 说明和代码示例。"""
    url = _PLUG_DETAIL_URL.format(id=plugin_id)
    try:
        result = _fetch_json(url, method="GET", timeout=10)
    except Exception as e:
        return f"查询插件详情失败：{e}"

    data = result.get("data", {})
    if not data:
        return f"未找到 id={plugin_id} 的插件。"

    name = data.get("name", "")
    author = data.get("auth", "")
    downloads = data.get("download", 0)
    versions = data.get("vList", [])

    lines = [
        f"# 插件：{name}",
        f"作者：{author} | 下载量：{downloads}",
        f"",
        f"## 加载方式",
        f"```python",
        f'from ascript.android import plug',
        f'plug.load("{name}")',
        f'import {name}',
        f"```",
        f"",
    ]

    if versions:
        latest = versions[0]
        lines.append(f"## 最新版本：{latest.get('version', '')}")
        desc = latest.get("desc", "")
        if desc:
            lines.append(f"简介：{desc}")
            lines.append("")
        info = latest.get("info", "")
        if info:
            lines.append("## 详细文档")
            lines.append(info)
            lines.append("")

        if len(versions) > 1:
            lines.append("## 历史版本")
            for v in versions[1:]:
                vdesc = v.get("desc", "")
                lines.append(f"- {v.get('version', '')} ({v.get('add_date', '')}) {vdesc}")

    return "\n".join(lines)


def web_selector_windows() -> dict[str, Any]:
    """获取 Android WebView 窗口列表。"""
    d = require_device()
    if d.platform != "android":
        return {"error": "此功能仅支持 Android 设备"}
    url = f"{d.base_url}/api/webselector/windows"
    return _fetch_json(url, method="GET", headers=d.headers)


def web_selector_dump(selector: str = "") -> dict[str, Any]:
    """获取 Android WebView 控件树。"""
    d = require_device()
    if d.platform != "android":
        return {"error": "此功能仅支持 Android 设备"}
    params = {}
    if selector:
        params["selector"] = selector
    url = f"{d.base_url}/api/webselector/dump"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return _fetch_json(url, method="GET", headers=d.headers)
