# AScript MCP 服务部署文档

## 概述

AScript MCP 服务为 AI 编程工具（Cursor、Trae、Claude Desktop 等）提供 ascript 自动化库的 API 文档查询能力，让大模型能写出正确的 Android/iOS/Windows 自动化代码。

服务使用 MCP (Model Context Protocol) 协议，通过 SSE (Server-Sent Events) 传输方式对外提供服务。

---

## 环境准备

- **操作系统**: Linux（推荐 Ubuntu 22.04+）
- **Python**: 3.10+（推荐 3.13）
- **端口**: 默认 8000（可配置）

---

## 部署步骤

### 1. 克隆代码

```bash
cd /opt
git clone <your-repo-url> ascript-mcp
cd ascript-mcp
```

### 2. 创建虚拟环境

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 生成 API 数据（可选）

如果 `src/ascript_mcp/api_data/` 下已有 JSON 文件则跳过此步。

如需重新提取（ascript 源码更新后）：

```bash
python scripts/extract_api.py /path/to/ascript-windows
```

这会从 ascript 源码中提取 API 文档，生成 `android.json`、`ios.json`、`windows.json`。

### 5. 测试启动

```bash
cd /opt/ascript-mcp
source .venv/bin/activate
pip install -e .
python -m ascript_mcp.server
```

看到类似输出说明启动成功：
```
AScript MCP Server 启动，端口: 8000
```

访问 `http://localhost:8000/sse` 确认 SSE 端点可用。

### 6. 自定义端口

通过环境变量设置：

```bash
export ASCRIPT_MCP_PORT=9000
python -m ascript_mcp.server
```

---

## 使用 systemd 管理服务

### 安装服务

```bash
# 复制 service 文件
sudo cp deploy/ascript-mcp.service /etc/systemd/system/

# 根据实际情况修改 service 文件中的路径和用户
sudo vim /etc/systemd/system/ascript-mcp.service

# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start ascript-mcp

# 设置开机自启
sudo systemctl enable ascript-mcp

# 查看状态
sudo systemctl status ascript-mcp

# 查看日志
sudo journalctl -u ascript-mcp -f
```

### 重启服务

```bash
sudo systemctl restart ascript-mcp
```

---

## Nginx 反向代理（可选）

SSE 需要特殊的 Nginx 配置（禁用缓冲），否则事件流会被截断。

```nginx
server {
    listen 443 ssl;
    server_name mcp.your-domain.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 关键配置：禁用缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        chunked_transfer_encoding off;

        # 超时设置（SSE 长连接）
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

---

## 客户端配置

### Cursor

在项目根目录或全局创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "ascript": {
      "url": "http://your-server:8000/sse"
    }
  }
}
```

如果使用了 Nginx + HTTPS：

```json
{
  "mcpServers": {
    "ascript": {
      "url": "https://mcp.your-domain.com/sse"
    }
  }
}
```

### Trae

在 Trae 设置中添加 MCP 服务器：

1. 打开 Trae 设置 → MCP
2. 点击「添加 MCP 服务器」
3. 类型选择 SSE
4. URL 填写：`http://your-server:8000/sse`
5. 名称填写：`ascript`

### Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "ascript": {
      "url": "http://your-server:8000/sse"
    }
  }
}
```

---

## 健康检查

```bash
# 检查服务是否存活
curl -s http://localhost:8000/health

# 检查 SSE 端点（会持续输出事件流，Ctrl+C 退出）
curl -N http://localhost:8000/sse
```

---

## 更新 API 数据

当 ascript 库的源码有更新时，需要重新提取 API 数据：

```bash
cd /opt/ascript-mcp
source .venv/bin/activate

# 重新提取（指向 ascript 源码目录）
python scripts/extract_api.py /path/to/ascript-windows

# 重启服务使新数据生效
sudo systemctl restart ascript-mcp
```

---

## 常见问题

### Q: 服务启动后客户端连不上？
- 检查防火墙是否开放了端口（默认 8000）
- 如果使用 Nginx，确认 SSE 缓冲已禁用
- 检查 `curl http://your-server:8000/health` 是否返回 OK

### Q: 大模型写的代码不够准确？
- 检查 API 数据是否是最新的（重新运行 extract_api.py）
- 确认 Cursor/Trae 中 MCP 服务已正确连接（工具列表中应显示 ascript 相关工具）

### Q: 如何修改监听端口？
- 设置环境变量 `ASCRIPT_MCP_PORT=9000`
- 或修改 systemd service 文件中的 Environment 行
