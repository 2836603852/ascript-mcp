# MCP tool reference

Owned AScript Workspace 1.8.0: 69 registered tools.

| Tool | Purpose | Required arguments |
|---|---|---|
| `get_platform_overview` | 获取指定平台(android/ios/windows)的 API 模块概览，包含模块名、描述、类和函数列表。 | `platform` |
| `get_module_apis` | 获取指定模块的完整 API 文档，支持模糊匹配。例如 'screen' 可匹配 'ascript.windows.screen'。返回函数签名、参数说明和文档。 | `platform`, `module` |
| `search_api` | 按关键词搜索 API，覆盖函数名、类名和文档说明。当不确定功能在哪个模块时使用。 | `query` |
| `get_code_example` | 获取常见自动化任务的可运行代码示例。 | `task`, `platform` |
| `get_setup_guide` | 获取指定平台的环境搭建和安装指南。 | `platform` |
| `auto_connect` | 从当前 AScript 工程目录自动连接设备。 | `project_path` |
| `scan_devices` | 扫描发现所有 AirScript 设备。 | None |
| `connect_device` | 连接 Android/iOS 设备。连接后才能使用截图、控件树等设备工具。 | `ip` |
| `observe_device` | 一次性获取设备当前状态：截图 + 控件树，比分开调用更快。 | None |
| `deploy_and_run` | 一步完成开发验证循环：上传代码 → 运行 → 收集日志 → 截图验证。 | `project_name`, `code` |
| `screen_capture` | 截取设备当前屏幕。返回 PNG 图片。用于查看设备当前界面状态。 | None |
| `dump_ui_tree` | 获取设备当前界面的控件树（UI 层级结构）。返回所有控件的 id、text、desc、className、rect、clickable 等属性。 | None |
| `test_selector` | 在设备上实时测试 Selector 选择器，验证是否能精准匹配到目标控件。 | None |
| `ocr` | 在设备屏幕上执行 OCR 文字识别。返回识别到的文字、位置坐标和置信度。 | None |
| `find_colors` | 多点找色：在屏幕上查找符合颜色条件的坐标。 | `colors` |
| `compare_colors` | 多点比色：检查屏幕指定位置的颜色是否匹配。 | `colors` |
| `create_project` | 在设备上创建新工程。上传文件前需要先创建工程。 | `name` |
| `list_python_packages` | 列出设备 AScript App 内已安装的 Python 第三方库（Android + iOS）。 | None |
| `get_device_status` | 获取设备完整运行状态（仅 Android）。一次性返回： | None |
| `list_projects` | 列出设备上的所有工程。 | None |
| `run_project` | 在设备上运行指定工程。 | `name` |
| `stop_project` | 停止设备上正在运行的工程。 | None |
| `eval_python` | 在设备主进程的 Python 上下文中直接 exec 任意代码，立即返回结果（Android + iOS）。 | `code` |
| `run_project_debug` | 以调试模式启动 Android 工程，让脚本可被 VS Code / Cursor 通过 debugpy attach 调试。 | `name` |
| `get_run_log` | 获取设备运行日志（实时收集指定秒数）。 | None |
| `list_plugins` | 查询 AScript 在线插件库，返回所有可用插件列表。 | None |
| `get_plugin_detail` | 获取指定插件的详细文档，包括 API 说明、参数、代码示例和版本历史。 | `plugin_id` |
| `get_project_files` | 获取设备上指定工程的文件树结构。 | `name` |
| `upload_file` | 上传文件到设备上的指定工程。content 为文件内容的 base64 编码。 | `project_name`, `relative_path`, `content_base64` |
| `workspace_login` | 自动登录开发者后台和 AI Studio；凭据从本机配置读取，不需要在每次工具调用中发送密码。 | None |
| `workspace_session_status` | 恢复或自动登录会话，返回后台和 AI Studio 的有效状态。 | None |
| `workspace_get_account` | 读取账号信息、会员状态与账户余额；不会充值或调用付费模型。 | None |
| `workspace_operations` | 读取本机写操作记录；写请求超时后先对账，禁止盲目重发。 | None |
| `backend_list_apps` | 分页读取开发者后台小程序列表。 | None |
| `backend_get_app` | 读取小程序详情、当前表单字段和源码包下载地址。 | `app_id` |
| `backend_create_app` | 上传本机 AS/IAS/WAS/IUAS 包并新增小程序。默认下架；明确 is_show=true 才公开。 | `fields`, `package_path` |
| `backend_update_app` | 修改指定小程序信息，或替换程序包；先读取当前字段并保留其他设置。 | `app_id`, `fields` |
| `backend_set_published` | 将指定小程序上架或下架；这是会影响用户可见性的实际业务写入。 | `app_id`, `published` |
| `backend_download_source` | 下载账号所属小程序已上传的源码程序包到本机，返回路径和 SHA256。 | `app_id` |
| `backend_delete_app` | 删除指定小程序。必须取得针对该目标的明确删除授权。 | `app_id`, `confirm` |
| `backend_list_databases` | 读取开发者后台数据库账户列表，包括数据库名、主机、端口和连接账号。 | None |
| `backend_get_database` | 按数据库名读取该账户的连接详情；不会执行 SQL 或修改数据库。 | `database_name` |
| `backend_list_resources` | 分页读取数据库、插件、Pip、UI 模板、模型、设备、激活码及消费记录等账号资源。 | `resource` |
| `cloud_list_projects` | 自动登录后获取 AI Studio 云端工程列表。 | None |
| `cloud_get_project` | 获取云端工程元信息，并可附带文件树。 | `project_id` |
| `cloud_create_project` | 新建独立云端 Android/iOS 工程。 | `name` |
| `cloud_rename_project` | 修改云端工程名称。 | `project_id`, `name` |
| `cloud_delete_project` | 删除云端工程及其文件；需针对该工程的明确删除授权。 | `project_id`, `confirm` |
| `cloud_get_tree` | 获取云端工程完整目录与文件树。 | `project_id` |
| `cloud_read_file` | 读取云端源文件及 revision。修改时将 revision 传给 cloud_write_file，避免覆盖别人的新修改。 | `project_id`, `path` |
| `cloud_write_file` | 按指定 revision 保存云端文本源码；版本冲突会报错，不自动覆盖或重试。 | `project_id`, `path`, `content`, `revision` |
| `cloud_create_entry` | 在云端工程中新增文件或文件夹。 | `project_id`, `name` |
| `cloud_move_entry` | 移动或重命名云端文件/目录。 | `project_id`, `source_path`, `destination_path` |
| `cloud_delete_entry` | 删除工程内指定文件/目录；需要明确授权，不能用来清理未知数据。 | `project_id`, `path`, `confirm` |
| `cloud_upload_file` | 上传本机文本或二进制文件到云端；默认不覆盖已有文件。 | `project_id`, `path`, `local_path` |
| `cloud_download` | 下载云端源文件或目录 ZIP；空路径下载工程根目录源码。 | `project_id` |
| `cloud_export_package` | 将云端工程导出成可部署的 .as/.ias 包，不需要连接手机。 | `project_id` |
| `cloud_import_package` | 上传本机 .as/.ias/.zip 并导入为新的云端工程。 | `local_path`, `name` |
| `cloud_import_directory` | 将本机含 __init__.py 的源码目录导入云端新工程；跳过依赖缓存和链接目录。 | `local_path`, `name` |
| `cloud_list_apps` | 获取 AI Studio 商业分发列表，含程序包地址、上下架和收费状态。 | None |
| `cloud_list_conversations` | 读取指定云端工程的历史对话列表，不发起模型调用。 | `project_id` |
| `cloud_get_conversation` | 读取指定工程的一条历史对话与消息，不调用付费模型。 | `project_id`, `conversation_id` |
| `cloud_publish_app` | 把指定云端工程发布为小程序；真实发布前须确认名称、收费与公开范围。 | `project_id`, `name` |
| `cloud_update_apps` | 用云端工程更新明确指定的小程序列表；返回每项结果，不自动重发失败批次。 | `project_id`, `app_ids` |
| `cloud_get_package_url` | 获取小程序独立 APP 打包页面链接；仅获取入口，不启动收费打包。 | `app_id` |
| `cloud_get_device` | 获取云端工程的设备连接与同步状态；与本地 USB/Wi-Fi 设备会话分别管理。 | `project_id` |
| `cloud_create_pairing` | 为明确选择的云端工程生成 AI Studio 设备配对码；用于云端设备绑定。 | `project_id` |
| `cloud_sync_device` | 把云端工程同步到已绑定设备；默认只同步，run=true 才运行。 | `project_id` |
| `cloud_disconnect_device` | 解除云端工程的设备连接；需要明确授权。 | `project_id`, `confirm` |

## Schemas

### get_platform_overview

```json
{
  "type": "object",
  "properties": {
    "platform": {
      "type": "string",
      "description": "目标平台：android、ios 或 windows",
      "enum": [
        "android",
        "ios",
        "windows"
      ]
    }
  },
  "required": [
    "platform"
  ]
}
```

### get_module_apis

```json
{
  "type": "object",
  "properties": {
    "platform": {
      "type": "string",
      "description": "目标平台：android、ios 或 windows",
      "enum": [
        "android",
        "ios",
        "windows"
      ]
    },
    "module": {
      "type": "string",
      "description": "模块名，如 'screen'、'action'、'node'"
    }
  },
  "required": [
    "platform",
    "module"
  ]
}
```

### search_api

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "搜索关键词，如 'click'、'ocr'、'截图'"
    },
    "platform": {
      "type": "string",
      "description": "可选，按平台过滤",
      "enum": [
        "android",
        "ios",
        "windows",
        ""
      ],
      "default": ""
    }
  },
  "required": [
    "query"
  ]
}
```

### get_code_example

```json
{
  "type": "object",
  "properties": {
    "task": {
      "type": "string",
      "description": "任务关键词，如 '点击'、'找图'、'OCR'、'滑动'"
    },
    "platform": {
      "type": "string",
      "description": "目标平台",
      "enum": [
        "android",
        "ios",
        "windows"
      ]
    }
  },
  "required": [
    "task",
    "platform"
  ]
}
```

### get_setup_guide

```json
{
  "type": "object",
  "properties": {
    "platform": {
      "type": "string",
      "description": "目标平台",
      "enum": [
        "android",
        "ios",
        "windows"
      ]
    }
  },
  "required": [
    "platform"
  ]
}
```

### auto_connect

```json
{
  "type": "object",
  "properties": {
    "project_path": {
      "type": "string",
      "description": "AScript 工程根目录的绝对路径"
    }
  },
  "required": [
    "project_path"
  ]
}
```

### scan_devices

```json
{
  "type": "object",
  "properties": {
    "port": {
      "type": "integer",
      "description": "局域网扫描端口，默认 9096",
      "default": 9096
    }
  }
}
```

### connect_device

```json
{
  "type": "object",
  "properties": {
    "ip": {
      "type": "string",
      "description": "设备 IP 地址（局域网）或 ADB 序列号"
    },
    "port": {
      "type": "integer",
      "description": "设备端口，默认 9096（ADB 模式忽略此参数）",
      "default": 9096
    },
    "password": {
      "type": "string",
      "description": "设备密码（公网模式下需要），默认为空",
      "default": ""
    },
    "connection_mode": {
      "type": "string",
      "description": "连接方式：LocalIP（默认，局域网）或 ADB（USB）",
      "enum": [
        "LocalIP",
        "ADB"
      ],
      "default": "LocalIP"
    }
  },
  "required": [
    "ip"
  ]
}
```

### observe_device

```json
{
  "type": "object",
  "properties": {}
}
```

### deploy_and_run

```json
{
  "type": "object",
  "properties": {
    "project_name": {
      "type": "string",
      "description": "工程名称"
    },
    "code": {
      "type": "string",
      "description": "Python 脚本代码内容"
    },
    "log_seconds": {
      "type": "number",
      "description": "收集日志的秒数，默认 5",
      "default": 5.0
    }
  },
  "required": [
    "project_name",
    "code"
  ]
}
```

### screen_capture

```json
{
  "type": "object",
  "properties": {}
}
```

### dump_ui_tree

```json
{
  "type": "object",
  "properties": {
    "mode": {
      "type": "integer",
      "description": "控件检索模式（Android），对应 get_device_status 返回的 run_mode.code：\n0 = 无障碍 - 简单（仅重要控件，run_mode=accessibility 时常用）\n1 = 无障碍 - 复杂（所有控件含布局节点）\n2 = 无障碍 - 简单 + 过滤系统层（状态栏/导航栏，推荐）\n3 = 无障碍 - 复杂 + 过滤系统层\n6 = 辅助控件（run_mode=hid 时用，对应 Selector.MODE_ASS）\n9 = Root 控件（run_mode=root 时用，对应 Selector.MODE_ROOT）\nSelector 类常量：MODE_ACC_SIMPLE=0 / MODE_ACC_ALL=1 / MODE_ASS=6 / MODE_ROOT=9。",
      "default": 0
    }
  }
}
```

### test_selector

```json
{
  "type": "object",
  "properties": {
    "text": {
      "type": "string",
      "description": "按文本内容匹配"
    },
    "id": {
      "type": "string",
      "description": "按资源 ID 匹配，如 'com.tencent.mm:id/xxx'"
    },
    "type": {
      "type": "string",
      "description": "按控件类型匹配，如 'TextView'、'Button'、'ImageView'"
    },
    "desc": {
      "type": "string",
      "description": "按内容描述匹配"
    },
    "clickable": {
      "type": "boolean",
      "description": "是否可点击"
    },
    "mode": {
      "type": "integer",
      "description": "检索模式（Android）：0=普通，1=复杂，2=简单过滤系统控件",
      "default": 0
    }
  }
}
```

### ocr

```json
{
  "type": "object",
  "properties": {
    "mode": {
      "type": "string",
      "description": "OCR 引擎：mlkit（默认,快）、paddle_v2、paddle_v3（最新）、tess",
      "enum": [
        "mlkit",
        "paddle_v2",
        "paddle_v3",
        "tess"
      ],
      "default": "mlkit"
    },
    "rect": {
      "type": "array",
      "items": {
        "type": "integer"
      },
      "description": "识别区域 [left, top, right, bottom]，不传则全屏"
    },
    "pattern": {
      "type": "string",
      "description": "正则表达式过滤结果"
    },
    "confidence": {
      "type": "number",
      "description": "置信度阈值 0.0-1.0，默认 0.1",
      "default": 0.1
    }
  }
}
```

### find_colors

```json
{
  "type": "object",
  "properties": {
    "colors": {
      "type": "string",
      "description": "颜色描述，如 '100,200,#FF0000|102,200,#00FF00'"
    },
    "rect": {
      "type": "array",
      "items": {
        "type": "integer"
      },
      "description": "搜索区域 [left, top, right, bottom]"
    },
    "diff": {
      "type": "number",
      "description": "相似度 0.0-1.0，默认 0.98",
      "default": 0.98
    }
  },
  "required": [
    "colors"
  ]
}
```

### compare_colors

```json
{
  "type": "object",
  "properties": {
    "colors": {
      "type": "string",
      "description": "颜色描述，如 '100,200,#FF0000|102,200,#00FF00'"
    },
    "diff": {
      "type": "number",
      "description": "相似度阈值，默认 0.9",
      "default": 0.9
    }
  },
  "required": [
    "colors"
  ]
}
```

### create_project

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "工程名称（英文/数字/下划线）"
    }
  },
  "required": [
    "name"
  ]
}
```

### list_python_packages

```json
{
  "type": "object",
  "properties": {}
}
```

### get_device_status

```json
{
  "type": "object",
  "properties": {}
}
```

### list_projects

```json
{
  "type": "object",
  "properties": {}
}
```

### run_project

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "工程名称"
    }
  },
  "required": [
    "name"
  ]
}
```

### stop_project

```json
{
  "type": "object",
  "properties": {}
}
```

### eval_python

```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "string",
      "description": "要执行的 Python 代码。必须将结果赋给 _result 变量。"
    },
    "image_path": {
      "type": "string",
      "description": "可选：传入已有图片路径，App 会注入为 _im_source 全局变量。"
    }
  },
  "required": [
    "code"
  ]
}
```

### run_project_debug

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "工程名称"
    }
  },
  "required": [
    "name"
  ]
}
```

### get_run_log

```json
{
  "type": "object",
  "properties": {
    "seconds": {
      "type": "number",
      "description": "收集日志的秒数，默认 3 秒",
      "default": 3.0
    }
  }
}
```

### list_plugins

```json
{
  "type": "object",
  "properties": {}
}
```

### get_plugin_detail

```json
{
  "type": "object",
  "properties": {
    "plugin_id": {
      "type": "integer",
      "description": "插件 ID（从 list_plugins 返回的 id 字段）"
    }
  },
  "required": [
    "plugin_id"
  ]
}
```

### get_project_files

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "工程名称"
    }
  },
  "required": [
    "name"
  ]
}
```

### upload_file

```json
{
  "type": "object",
  "properties": {
    "project_name": {
      "type": "string",
      "description": "工程名称"
    },
    "relative_path": {
      "type": "string",
      "description": "文件在工程内的相对路径，如 '__init__.py' 或 'res/img/1.png'"
    },
    "content_base64": {
      "type": "string",
      "description": "文件内容的 base64 编码"
    }
  },
  "required": [
    "project_name",
    "relative_path",
    "content_base64"
  ]
}
```

### workspace_login

```json
{
  "type": "object",
  "properties": {
    "service": {
      "type": "string",
      "description": "登录服务",
      "enum": [
        "both",
        "admin",
        "cloud"
      ],
      "default": "both"
    },
    "force": {
      "type": "boolean",
      "description": "强制换取新会话",
      "default": false
    }
  },
  "required": [],
  "additionalProperties": false
}
```

### workspace_session_status

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### workspace_get_account

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### workspace_operations

```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "description": "最近记录数",
      "minimum": 1,
      "maximum": 200,
      "default": 20
    }
  },
  "required": [],
  "additionalProperties": false
}
```

### backend_list_apps

```json
{
  "type": "object",
  "properties": {
    "page": {
      "type": "integer",
      "description": "页码",
      "minimum": 1,
      "default": 1
    },
    "per_page": {
      "type": "integer",
      "description": "每页条数",
      "minimum": 1,
      "maximum": 100,
      "default": 20
    },
    "filters": {
      "type": "object",
      "description": "后台列表的筛选字段"
    }
  },
  "required": [],
  "additionalProperties": false
}
```

### backend_get_app

```json
{
  "type": "object",
  "properties": {
    "app_id": {
      "type": "integer",
      "description": "账号所属小程序 ID",
      "minimum": 1
    }
  },
  "required": [
    "app_id"
  ],
  "additionalProperties": false
}
```

### backend_create_app

```json
{
  "type": "object",
  "properties": {
    "fields": {
      "type": "object",
      "description": "仅修改指定字段，保留后台现有其他值",
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "description": "名称"
        },
        "desc": {
          "type": "string",
          "description": "详情 HTML"
        },
        "format_ver": {
          "type": "integer",
          "enum": [
            3,
            4
          ]
        },
        "is_free": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "pro_card": {
          "type": "integer",
          "description": "激活码设置",
          "minimum": 0
        },
        "max_device": {
          "type": "integer",
          "description": "最大设备数，0 表示不限",
          "minimum": 0
        },
        "card_bind_device": {
          "type": "boolean",
          "description": "card_bind_device",
          "default": false
        },
        "autoBuyDevice": {
          "type": "boolean",
          "description": "autoBuyDevice",
          "default": false
        },
        "is_hide": {
          "type": "boolean",
          "description": "is_hide",
          "default": false
        },
        "is_show": {
          "type": "boolean",
          "description": "is_show",
          "default": false
        }
      }
    },
    "package_path": {
      "type": "string",
      "description": "本机程序包完整路径"
    }
  },
  "required": [
    "fields",
    "package_path"
  ],
  "additionalProperties": false
}
```

### backend_update_app

```json
{
  "type": "object",
  "properties": {
    "app_id": {
      "type": "integer",
      "description": "账号所属小程序 ID",
      "minimum": 1
    },
    "fields": {
      "type": "object",
      "description": "仅修改指定字段，保留后台现有其他值",
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "description": "名称"
        },
        "desc": {
          "type": "string",
          "description": "详情 HTML"
        },
        "format_ver": {
          "type": "integer",
          "enum": [
            3,
            4
          ]
        },
        "is_free": {
          "type": "integer",
          "enum": [
            0,
            1
          ]
        },
        "pro_card": {
          "type": "integer",
          "description": "激活码设置",
          "minimum": 0
        },
        "max_device": {
          "type": "integer",
          "description": "最大设备数，0 表示不限",
          "minimum": 0
        },
        "card_bind_device": {
          "type": "boolean",
          "description": "card_bind_device",
          "default": false
        },
        "autoBuyDevice": {
          "type": "boolean",
          "description": "autoBuyDevice",
          "default": false
        },
        "is_hide": {
          "type": "boolean",
          "description": "is_hide",
          "default": false
        },
        "is_show": {
          "type": "boolean",
          "description": "is_show",
          "default": false
        }
      }
    },
    "package_path": {
      "type": "string",
      "description": "可选：本机新程序包路径"
    }
  },
  "required": [
    "app_id",
    "fields"
  ],
  "additionalProperties": false
}
```

### backend_set_published

```json
{
  "type": "object",
  "properties": {
    "app_id": {
      "type": "integer",
      "description": "账号所属小程序 ID",
      "minimum": 1
    },
    "published": {
      "type": "boolean",
      "description": "true 上架，false 下架",
      "default": false
    }
  },
  "required": [
    "app_id",
    "published"
  ],
  "additionalProperties": false
}
```

### backend_download_source

```json
{
  "type": "object",
  "properties": {
    "app_id": {
      "type": "integer",
      "description": "账号所属小程序 ID",
      "minimum": 1
    },
    "destination": {
      "type": "string",
      "description": "本机文件路径或目录；省略则保存到配置的输出目录"
    },
    "overwrite": {
      "type": "boolean",
      "description": "是否覆盖本机已存在的目标文件",
      "default": false
    }
  },
  "required": [
    "app_id"
  ],
  "additionalProperties": false
}
```

### backend_delete_app

```json
{
  "type": "object",
  "properties": {
    "app_id": {
      "type": "integer",
      "description": "账号所属小程序 ID",
      "minimum": 1
    },
    "confirm": {
      "type": "boolean",
      "description": "仅在用户明确授权删除或断开该目标时设置 true",
      "default": false
    }
  },
  "required": [
    "app_id",
    "confirm"
  ],
  "additionalProperties": false
}
```

### backend_list_databases

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### backend_get_database

```json
{
  "type": "object",
  "properties": {
    "database_name": {
      "type": "string",
      "description": "backend_list_databases 返回的数据库名"
    }
  },
  "required": [
    "database_name"
  ],
  "additionalProperties": false
}
```

### backend_list_resources

```json
{
  "type": "object",
  "properties": {
    "resource": {
      "type": "string",
      "description": "资源类型",
      "enum": [
        "apps",
        "databases",
        "plugins",
        "pip",
        "ui_templates",
        "models",
        "devices",
        "activation_codes",
        "usage",
        "recharges",
        "device_orders"
      ]
    },
    "page": {
      "type": "integer",
      "description": "页码",
      "minimum": 1,
      "default": 1
    },
    "per_page": {
      "type": "integer",
      "description": "每页条数",
      "minimum": 1,
      "maximum": 100,
      "default": 20
    },
    "filters": {
      "type": "object",
      "description": "后台列表的筛选字段"
    }
  },
  "required": [
    "resource"
  ],
  "additionalProperties": false
}
```

### cloud_list_projects

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### cloud_get_project

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "include_tree": {
      "type": "boolean",
      "description": "附带文件树",
      "default": true
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_create_project

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "工程名，最多 48 字符"
    },
    "platform": {
      "type": "string",
      "description": "平台",
      "enum": [
        "android",
        "ios"
      ],
      "default": "android"
    }
  },
  "required": [
    "name"
  ],
  "additionalProperties": false
}
```

### cloud_rename_project

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "name": {
      "type": "string",
      "description": "新名称"
    }
  },
  "required": [
    "project_id",
    "name"
  ],
  "additionalProperties": false
}
```

### cloud_delete_project

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "confirm": {
      "type": "boolean",
      "description": "仅在用户明确授权删除或断开该目标时设置 true",
      "default": false
    }
  },
  "required": [
    "project_id",
    "confirm"
  ],
  "additionalProperties": false
}
```

### cloud_get_tree

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_read_file

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "path": {
      "type": "string",
      "description": "工程内相对文件路径"
    },
    "offset": {
      "type": "integer",
      "description": "文本起始字符",
      "minimum": 0,
      "default": 0
    },
    "max_chars": {
      "type": "integer",
      "description": "最多返回字符数；大文件请分段读取或下载",
      "minimum": 1,
      "maximum": 200000,
      "default": 60000
    }
  },
  "required": [
    "project_id",
    "path"
  ],
  "additionalProperties": false
}
```

### cloud_write_file

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "path": {
      "type": "string",
      "description": "工程内相对文件路径"
    },
    "content": {
      "type": "string",
      "description": "完整新文件内容"
    },
    "revision": {
      "type": "string",
      "description": "最近 cloud_read_file 返回的 revision"
    }
  },
  "required": [
    "project_id",
    "path",
    "content",
    "revision"
  ],
  "additionalProperties": false
}
```

### cloud_create_entry

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "name": {
      "type": "string",
      "description": "单一文件或目录名"
    },
    "type": {
      "type": "string",
      "description": "类型",
      "enum": [
        "file",
        "directory"
      ],
      "default": "file"
    },
    "parent_path": {
      "type": "string",
      "description": "父目录，空字符串为工程根目录",
      "default": ""
    }
  },
  "required": [
    "project_id",
    "name"
  ],
  "additionalProperties": false
}
```

### cloud_move_entry

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "source_path": {
      "type": "string",
      "description": "现有相对路径"
    },
    "destination_path": {
      "type": "string",
      "description": "目标相对路径"
    }
  },
  "required": [
    "project_id",
    "source_path",
    "destination_path"
  ],
  "additionalProperties": false
}
```

### cloud_delete_entry

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "path": {
      "type": "string",
      "description": "工程内路径"
    },
    "confirm": {
      "type": "boolean",
      "description": "仅在用户明确授权删除或断开该目标时设置 true",
      "default": false
    }
  },
  "required": [
    "project_id",
    "path",
    "confirm"
  ],
  "additionalProperties": false
}
```

### cloud_upload_file

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "path": {
      "type": "string",
      "description": "云端目标相对路径"
    },
    "local_path": {
      "type": "string",
      "description": "本机文件完整路径"
    },
    "overwrite": {
      "type": "boolean",
      "description": "明确覆盖已有文件",
      "default": false
    }
  },
  "required": [
    "project_id",
    "path",
    "local_path"
  ],
  "additionalProperties": false
}
```

### cloud_download

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "path": {
      "type": "string",
      "description": "云端文件/目录相对路径，空字符串为根",
      "default": ""
    },
    "destination": {
      "type": "string",
      "description": "本机文件路径或目录；省略则保存到配置的输出目录"
    },
    "overwrite": {
      "type": "boolean",
      "description": "是否覆盖本机已存在的目标文件",
      "default": false
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_export_package

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "destination": {
      "type": "string",
      "description": "本机文件路径或目录；省略则保存到配置的输出目录"
    },
    "overwrite": {
      "type": "boolean",
      "description": "是否覆盖本机已存在的目标文件",
      "default": false
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_import_package

```json
{
  "type": "object",
  "properties": {
    "local_path": {
      "type": "string",
      "description": "本机工程包路径"
    },
    "name": {
      "type": "string",
      "description": "新工程名"
    },
    "platform": {
      "type": "string",
      "description": "平台，可按包后缀推断",
      "enum": [
        "android",
        "ios"
      ]
    }
  },
  "required": [
    "local_path",
    "name"
  ],
  "additionalProperties": false
}
```

### cloud_import_directory

```json
{
  "type": "object",
  "properties": {
    "local_path": {
      "type": "string",
      "description": "本机工程目录"
    },
    "name": {
      "type": "string",
      "description": "新工程名"
    },
    "platform": {
      "type": "string",
      "description": "平台",
      "enum": [
        "android",
        "ios"
      ],
      "default": "android"
    }
  },
  "required": [
    "local_path",
    "name"
  ],
  "additionalProperties": false
}
```

### cloud_list_apps

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### cloud_list_conversations

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_get_conversation

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "conversation_id": {
      "type": "string",
      "description": "历史对话 ID"
    }
  },
  "required": [
    "project_id",
    "conversation_id"
  ],
  "additionalProperties": false
}
```

### cloud_publish_app

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "name": {
      "type": "string",
      "description": "小程序名"
    },
    "desc": {
      "type": "string",
      "description": "描述",
      "default": ""
    },
    "is_free": {
      "type": "boolean",
      "description": "免费程序",
      "default": true
    },
    "is_v4": {
      "type": "boolean",
      "description": "Android 使用 V4 加密",
      "default": true
    }
  },
  "required": [
    "project_id",
    "name"
  ],
  "additionalProperties": false
}
```

### cloud_update_apps

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "app_ids": {
      "type": "array",
      "items": {
        "type": "integer",
        "description": "小程序 ID",
        "minimum": 1
      },
      "minItems": 1,
      "uniqueItems": true
    },
    "is_v4": {
      "type": "boolean",
      "description": "Android 使用 V4 加密",
      "default": true
    }
  },
  "required": [
    "project_id",
    "app_ids"
  ],
  "additionalProperties": false
}
```

### cloud_get_package_url

```json
{
  "type": "object",
  "properties": {
    "app_id": {
      "type": "integer",
      "description": "账号所属小程序 ID",
      "minimum": 1
    }
  },
  "required": [
    "app_id"
  ],
  "additionalProperties": false
}
```

### cloud_get_device

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_create_pairing

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_sync_device

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "run": {
      "type": "boolean",
      "description": "同步后运行脚本",
      "default": false
    }
  },
  "required": [
    "project_id"
  ],
  "additionalProperties": false
}
```

### cloud_disconnect_device

```json
{
  "type": "object",
  "properties": {
    "project_id": {
      "type": "string",
      "description": "云端工程 ID，从 cloud_list_projects 获取"
    },
    "confirm": {
      "type": "boolean",
      "description": "仅在用户明确授权删除或断开该目标时设置 true",
      "default": false
    }
  },
  "required": [
    "project_id",
    "confirm"
  ],
  "additionalProperties": false
}
```
