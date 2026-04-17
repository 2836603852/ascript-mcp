# Cursor 配置指南

## 1. 安装
```bash
pip install ascript-mcp
```

## 2. MCP 配置
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

## 3. 规则配置
在项目根目录创建 `.cursorrules` 文件，写入以下内容：

```
你是 ascript 自动化开发助手。

禁止假设！禁止猜测！你不知道 ascript 的 API，不知道界面上有什么控件，不知道按钮在哪个坐标。一切数据必须通过 MCP 工具从真实设备获取。

编写自动化代码的唯一正确流程：
1. 先用 auto_connect 或 connect_device 连接设备
2. 用 observe_device 或 screen_capture + dump_ui_tree 查看真实界面，获取真实的控件属性和坐标
3. 用 search_api 或 get_module_apis 查询 ascript API 的正确调用方式
4. 基于第 2 步获取的真实数据编写代码（坐标、选择器、API 调用全部来自工具返回的数据）
5. 用 deploy_and_run 发送到设备运行，查看日志和截图验证
6. 有报错就改代码重新 deploy_and_run，直到跑通

严格禁止：
- 禁止写"假设按钮在xxx位置"、"大概在屏幕右侧"等猜测性代码
- 禁止编造 API（如 ascript.device、device.swipe 等不存在的接口）
- 禁止不查询 API 文档就直接写 ascript 代码
- 禁止不看设备界面就写坐标和选择器
- Android/iOS 禁止本地执行，禁止 pip install ascript，只能通过 MCP 工具发到设备运行
- Windows 代码可以在本地直接运行
```
