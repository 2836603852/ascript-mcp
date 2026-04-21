# Contributing to ascript-mcp

感谢你愿意参与 / Thanks for your interest in contributing.

## 开发环境 / Dev setup

```bash
git clone https://github.com/ascript-cn/ascript-mcp.git
cd ascript-mcp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

运行 stdio 模式 / Run the stdio server:

```bash
python -m ascript_mcp.local
```

运行 SSE 模式 / Run the SSE server:

```bash
uvicorn ascript_mcp.server:app --host 0.0.0.0 --port 8000
```

## 提交 Issue / Filing issues

- **Bug 报告**：请用 Bug 模板，提供最小复现步骤 + 你的 Python 版本 + 操作系统
- **Feature request**：说明使用场景；空泛的"加个 X"优先级很低
- **API 文档缺漏**：如果 `search_api` / `get_module_apis` 返回的数据与 [docs.airscript.cn](https://docs.airscript.cn) 不一致，欢迎报告

## 提交 PR / Pull requests

1. Fork 仓库 → 新建分支 → 改动 → 提 PR
2. 提交信息用英文或中文都行，但**描述清楚 why**，不是 what
3. 小 PR 比大 PR 更容易 review
4. 涉及新 MCP 工具时，请同时更新 `README.md` 和 `README_EN.md` 的工具列表

## 代码风格 / Code style

- Python ≥ 3.10
- 函数/类需要 docstring（中文英文皆可）
- 避免引入新的重量级依赖，当前只依赖 `mcp`、`uvicorn`、`starlette`

## 重新生成 API 数据 / Regenerating API data

当 ascript 主库更新后：

```bash
python scripts/extract_api.py /path/to/ascript-source
```

会覆盖 `src/ascript_mcp/api_data/*.json`。

## 行为准则 / Code of conduct

请尊重所有贡献者。骚扰、人身攻击、政治/宗教口水战等内容会被直接删除，账号会被屏蔽。

Be respectful. Harassment or personal attacks will be removed and the account blocked.

## 许可 / License

提交的任何代码默认以 [MIT 协议](./LICENSE) 发布，与本仓库一致。

By submitting code you agree it's released under the repo's MIT license.
