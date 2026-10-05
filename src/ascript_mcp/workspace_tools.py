"""MCP schemas and dispatch for the owned workspace extension."""

from __future__ import annotations

from mcp.types import Tool, ToolAnnotations

from .backend import RESOURCE_PATHS, WorkspaceError, get_client
from .cloud import CloudClient


def string(description: str, **extras) -> dict:
    return {"type": "string", "description": description, **extras}


def boolean(description: str, default: bool = False) -> dict:
    return {"type": "boolean", "description": description, "default": default}


def integer(description: str, minimum: int = 1, **extras) -> dict:
    return {"type": "integer", "description": description, "minimum": minimum, **extras}


PROJECT = {"project_id": string("云端工程 ID，从 cloud_list_projects 获取")}
APP = {"app_id": integer("账号所属小程序 ID")}
CONFIRM = {"confirm": boolean("仅在用户明确授权删除或断开该目标时设置 true")}
DOWNLOAD = {"destination": string("本机文件路径或目录；省略则保存到配置的输出目录"),
            "overwrite": boolean("是否覆盖本机已存在的目标文件")}
PAGING = {"page": integer("页码", default=1),
          "per_page": integer("每页条数", maximum=100, default=20),
          "filters": {"type": "object", "description": "后台列表的筛选字段"}}
FIELDS = {"type": "object", "description": "仅修改指定字段，保留后台现有其他值",
          "additionalProperties": False, "properties": {
              "name": string("名称"), "desc": string("详情 HTML"),
              "format_ver": {"type": "integer", "enum": [3, 4]},
              "is_free": {"type": "integer", "enum": [0, 1]},
              "pro_card": integer("激活码设置", minimum=0),
              "max_device": integer("最大设备数，0 表示不限", minimum=0),
              **{k: boolean(k) for k in ("card_bind_device", "autoBuyDevice", "is_hide", "is_show")}}}

# name -> (description, properties, required, domain, method, read_only, destructive)
SPECS = {}


def add(name, description, properties, required, domain, method, read_only=True, destructive=False):
    SPECS[name] = (description, properties, required, domain, method, read_only, destructive)


add("workspace_login", "自动登录开发者后台和 AI Studio；凭据从本机配置读取，不需要在每次工具调用中发送密码。",
    {"service": string("登录服务", enum=["both", "admin", "cloud"], default="both"),
     "force": boolean("强制换取新会话")}, [], "workspace", "login", False)
add("workspace_session_status", "恢复或自动登录会话，返回后台和 AI Studio 的有效状态。",
    {}, [], "workspace", "session_status")
add("workspace_get_account", "读取账号信息、会员状态与账户余额；不会充值或调用付费模型。",
    {}, [], "workspace", "account")
add("workspace_operations", "读取本机写操作记录；写请求超时后先对账，禁止盲目重发。",
    {"limit": integer("最近记录数", maximum=200, default=20)}, [], "workspace", "operations")
add("backend_list_apps", "分页读取开发者后台小程序列表。", PAGING, [], "special", "list_apps")
add("backend_get_app", "读取小程序详情、当前表单字段和源码包下载地址。", APP,
    ["app_id"], "workspace", "get_app")
add("backend_create_app", "上传本机 AS/IAS/WAS/IUAS 包并新增小程序。默认下架；明确 is_show=true 才公开。",
    {"fields": FIELDS, "package_path": string("本机程序包完整路径")},
    ["fields", "package_path"], "workspace", "save_app", False)
add("backend_update_app", "修改指定小程序信息，或替换程序包；先读取当前字段并保留其他设置。",
    {**APP, "fields": FIELDS, "package_path": string("可选：本机新程序包路径")},
    ["app_id", "fields"], "workspace", "save_app", False)
add("backend_set_published", "将指定小程序上架或下架；这是会影响用户可见性的实际业务写入。",
    {**APP, "published": boolean("true 上架，false 下架")},
    ["app_id", "published"], "special", "set_published", False)
add("backend_download_source", "下载账号所属小程序已上传的源码程序包到本机，返回路径和 SHA256。",
    {**APP, **DOWNLOAD}, ["app_id"], "workspace", "download_source")
add("backend_delete_app", "删除指定小程序。必须取得针对该目标的明确删除授权。",
    {**APP, **CONFIRM}, ["app_id", "confirm"], "workspace", "delete_app", False, True)
add("backend_list_databases", "读取开发者后台数据库账户列表，包括数据库名、主机、端口和连接账号。",
    {}, [], "special", "list_databases")
add("backend_get_database", "按数据库名读取该账户的连接详情；不会执行 SQL 或修改数据库。",
    {"database_name": string("backend_list_databases 返回的数据库名")},
    ["database_name"], "special", "get_database")
add("backend_list_resources", "分页读取数据库、插件、Pip、UI 模板、模型、设备、激活码及消费记录等账号资源。",
    {"resource": string("资源类型", enum=list(RESOURCE_PATHS)), **PAGING},
    ["resource"], "workspace", "list_resources")

add("cloud_list_projects", "自动登录后获取 AI Studio 云端工程列表。", {}, [], "cloud", "list_projects")
add("cloud_get_project", "获取云端工程元信息，并可附带文件树。",
    {**PROJECT, "include_tree": boolean("附带文件树", True)}, ["project_id"], "cloud", "get_project")
add("cloud_create_project", "新建独立云端 Android/iOS 工程。",
    {"name": string("工程名，最多 48 字符"), "platform": string("平台", enum=["android", "ios"], default="android")},
    ["name"], "cloud", "create_project", False)
add("cloud_rename_project", "修改云端工程名称。", {**PROJECT, "name": string("新名称")},
    ["project_id", "name"], "cloud", "rename_project", False)
add("cloud_delete_project", "删除云端工程及其文件；需针对该工程的明确删除授权。", {**PROJECT, **CONFIRM},
    ["project_id", "confirm"], "cloud", "delete_project", False, True)
add("cloud_get_tree", "获取云端工程完整目录与文件树。", PROJECT, ["project_id"], "cloud", "get_tree")
add("cloud_read_file", "读取云端源文件及 revision。修改时将 revision 传给 cloud_write_file，避免覆盖别人的新修改。",
    {**PROJECT, "path": string("工程内相对文件路径"), "offset": integer("文本起始字符", minimum=0, default=0),
     "max_chars": integer("最多返回字符数；大文件请分段读取或下载", maximum=200000, default=60000)},
    ["project_id", "path"], "cloud", "read_file")
add("cloud_write_file", "按指定 revision 保存云端文本源码；版本冲突会报错，不自动覆盖或重试。",
    {**PROJECT, "path": string("工程内相对文件路径"), "content": string("完整新文件内容"),
     "revision": string("最近 cloud_read_file 返回的 revision")},
    ["project_id", "path", "content", "revision"], "cloud", "write_file", False)
add("cloud_create_entry", "在云端工程中新增文件或文件夹。",
    {**PROJECT, "name": string("单一文件或目录名"), "type": string("类型", enum=["file", "directory"], default="file"),
     "parent_path": string("父目录，空字符串为工程根目录", default="")},
    ["project_id", "name"], "cloud", "create_entry", False)
add("cloud_move_entry", "移动或重命名云端文件/目录。",
    {**PROJECT, "source_path": string("现有相对路径"), "destination_path": string("目标相对路径")},
    ["project_id", "source_path", "destination_path"], "cloud", "move_entry", False)
add("cloud_delete_entry", "删除工程内指定文件/目录；需要明确授权，不能用来清理未知数据。",
    {**PROJECT, "path": string("工程内路径"), **CONFIRM},
    ["project_id", "path", "confirm"], "cloud", "delete_entry", False, True)
add("cloud_upload_file", "上传本机文本或二进制文件到云端；默认不覆盖已有文件。",
    {**PROJECT, "path": string("云端目标相对路径"), "local_path": string("本机文件完整路径"),
     "overwrite": boolean("明确覆盖已有文件")},
    ["project_id", "path", "local_path"], "cloud", "upload_file", False)
add("cloud_download", "下载云端源文件或目录 ZIP；空路径下载工程根目录源码。",
    {**PROJECT, "path": string("云端文件/目录相对路径，空字符串为根", default=""), **DOWNLOAD},
    ["project_id"], "cloud", "download")
add("cloud_export_package", "将云端工程导出成可部署的 .as/.ias 包，不需要连接手机。",
    {**PROJECT, **DOWNLOAD}, ["project_id"], "cloud", "export_package")
add("cloud_import_package", "上传本机 .as/.ias/.zip 并导入为新的云端工程。",
    {"local_path": string("本机工程包路径"), "name": string("新工程名"),
     "platform": string("平台，可按包后缀推断", enum=["android", "ios"])},
    ["local_path", "name"], "cloud", "import_package", False)
add("cloud_import_directory", "将本机含 __init__.py 的源码目录导入云端新工程；跳过依赖缓存和链接目录。",
    {"local_path": string("本机工程目录"), "name": string("新工程名"),
     "platform": string("平台", enum=["android", "ios"], default="android")},
    ["local_path", "name"], "cloud", "import_directory", False)
add("cloud_list_apps", "获取 AI Studio 商业分发列表，含程序包地址、上下架和收费状态。",
    {}, [], "cloud", "list_apps")
add("cloud_list_conversations", "读取指定云端工程的历史对话列表，不发起模型调用。",
    PROJECT, ["project_id"], "cloud", "list_conversations")
add("cloud_get_conversation", "读取指定工程的一条历史对话与消息，不调用付费模型。",
    {**PROJECT, "conversation_id": string("历史对话 ID")},
    ["project_id", "conversation_id"], "cloud", "get_conversation")
add("cloud_publish_app", "把指定云端工程发布为小程序；真实发布前须确认名称、收费与公开范围。",
    {**PROJECT, "name": string("小程序名"), "desc": string("描述", default=""),
     "is_free": boolean("免费程序", True), "is_v4": boolean("Android 使用 V4 加密", True)},
    ["project_id", "name"], "cloud", "publish_app", False)
add("cloud_update_apps", "用云端工程更新明确指定的小程序列表；返回每项结果，不自动重发失败批次。",
    {**PROJECT, "app_ids": {"type": "array", "items": integer("小程序 ID"), "minItems": 1, "uniqueItems": True},
     "is_v4": boolean("Android 使用 V4 加密", True)},
    ["project_id", "app_ids"], "cloud", "update_apps", False)
add("cloud_get_package_url", "获取小程序独立 APP 打包页面链接；仅获取入口，不启动收费打包。",
    APP, ["app_id"], "cloud", "package_url")
add("cloud_get_device", "获取云端工程的设备连接与同步状态；与本地 USB/Wi-Fi 设备会话分别管理。",
    PROJECT, ["project_id"], "cloud", "device_status")
add("cloud_create_pairing", "为明确选择的云端工程生成 AI Studio 设备配对码；用于云端设备绑定。",
    PROJECT, ["project_id"], "cloud", "create_pairing", False)
add("cloud_sync_device", "把云端工程同步到已绑定设备；默认只同步，run=true 才运行。",
    {**PROJECT, "run": boolean("同步后运行脚本")}, ["project_id"], "cloud", "sync_device", False)
add("cloud_disconnect_device", "解除云端工程的设备连接；需要明确授权。", {**PROJECT, **CONFIRM},
    ["project_id", "confirm"], "cloud", "disconnect_device", False, True)


def list_workspace_tools() -> list[Tool]:
    return [Tool(name=name, description=spec[0], inputSchema={"type": "object",
                 "properties": spec[1], "required": spec[2], "additionalProperties": False},
                 annotations=ToolAnnotations(readOnlyHint=spec[5], destructiveHint=spec[6],
                                             openWorldHint=True))
            for name, spec in SPECS.items()]


def dispatch_workspace(name: str, args: dict):
    spec = SPECS[name]
    client = get_client()
    domain, method = spec[3], spec[4]
    if domain == "cloud":
        if method == "read_file":
            args = {"max_chars": 60000, **args}
        return getattr(CloudClient(client), method)(**args)
    if domain == "workspace":
        return getattr(client, method)(**args)
    if method == "list_apps":
        return client.list_resources("apps", **args)
    if method == "list_databases":
        return client.list_resources("databases")
    if method == "get_database":
        rows = client.list_resources("databases")["rows"]
        row = next((r for r in rows if r.get("db") == args["database_name"]), None)
        if row is None:
            raise WorkspaceError("账号下未找到该数据库。", "DATABASE_NOT_FOUND", 404)
        return row
    if method == "set_published":
        return client.save_app({"is_show": args["published"]}, app_id=args["app_id"])
    raise ValueError("未知工具处理方法")
