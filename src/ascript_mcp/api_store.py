"""API 数据加载与查询模块。

负责从 api_data 目录加载 JSON 格式的 API 文档，
并提供平台概览、模块详情、关键词搜索等查询能力。
"""

import json
import os
from typing import Any, Optional


# 支持的平台列表
VALID_PLATFORMS = ("android", "ios", "windows")


class ApiStore:
    """API 数据仓库，提供加载和查询功能。"""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """延迟加载：首次查询时才读取 JSON 文件。"""
        if self._loaded:
            return
        data_dir = os.path.join(os.path.dirname(__file__), "api_data")
        for platform in VALID_PLATFORMS:
            json_path = os.path.join(data_dir, f"{platform}.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    self._data[platform] = json.load(f)
        self._loaded = True

    # ------------------------------------------------------------------
    # 公开查询接口
    # ------------------------------------------------------------------

    def get_platform_overview(self, platform: str) -> str:
        """返回指定平台所有模块的概览信息。

        包含每个模块的名称、描述，以及其下主要的类和函数列表。
        """
        self._ensure_loaded()
        platform = platform.strip().lower()
        if platform not in self._data:
            return f"错误：不支持的平台 '{platform}'。支持的平台：{', '.join(VALID_PLATFORMS)}"

        modules = self._data[platform].get("modules", [])
        lines: list[str] = [f"# {platform.upper()} 平台 API 概览\n"]
        lines.append(f"共 {len(modules)} 个模块：\n")

        for mod in modules:
            module_name = mod["module"]
            docstring = (mod.get("docstring") or "").split("\n")[0]
            lines.append(f"## {module_name}")
            if docstring:
                lines.append(f"  {docstring}")

            # 列出类
            classes = mod.get("classes", [])
            if classes:
                cls_names = [c["name"] for c in classes]
                lines.append(f"  类: {', '.join(cls_names)}")

            # 列出函数
            functions = mod.get("functions", [])
            if functions:
                func_names = [f["name"] for f in functions]
                lines.append(f"  函数: {', '.join(func_names)}")

            lines.append("")

        return "\n".join(lines)

    def get_module_apis(self, platform: str, module: str) -> str:
        """返回某个模块的完整 API 文档。

        支持模糊匹配：用户输入 "screen" 可匹配 "ascript.windows.screen" 等。
        如果有多个匹配结果，返回所有匹配模块的文档。
        """
        self._ensure_loaded()
        platform = platform.strip().lower()
        if platform not in self._data:
            return f"错误：不支持的平台 '{platform}'。支持的平台：{', '.join(VALID_PLATFORMS)}"

        module_query = module.strip().lower()
        modules = self._data[platform].get("modules", [])
        matched = self._fuzzy_match_modules(modules, module_query)

        if not matched:
            all_names = [m["module"] for m in modules]
            return (
                f"错误：在 {platform} 平台下未找到匹配 '{module}' 的模块。\n"
                f"可用模块：\n" + "\n".join(f"  - {n}" for n in all_names)
            )

        parts: list[str] = []
        for mod in matched:
            parts.append(self._format_module(mod))

        return "\n\n".join(parts)

    def search_api(self, query: str, platform: Optional[str] = None) -> str:
        """按关键词搜索 API（函数名、类名、docstring）。

        当 platform 为空或 None 时搜索全部平台。
        """
        self._ensure_loaded()
        query_lower = query.strip().lower()
        if not query_lower:
            return "错误：搜索关键词不能为空。"

        platforms_to_search: list[str] = []
        if platform and platform.strip():
            p = platform.strip().lower()
            if p not in self._data:
                return f"错误：不支持的平台 '{platform}'。支持的平台：{', '.join(VALID_PLATFORMS)}"
            platforms_to_search = [p]
        else:
            platforms_to_search = list(self._data.keys())

        results: list[str] = []

        for plat in platforms_to_search:
            modules = self._data[plat].get("modules", [])
            for mod in modules:
                module_name = mod["module"]
                # 搜索模块级函数
                for func in mod.get("functions", []):
                    if self._match(query_lower, func):
                        results.append(
                            f"[{plat}] {module_name}.{func['name']}()\n"
                            f"  {self._one_line_doc(func)}"
                        )
                # 搜索类及其方法
                for cls in mod.get("classes", []):
                    if self._match_class(query_lower, cls):
                        results.append(
                            f"[{plat}] {module_name}.{cls['name']} (类)\n"
                            f"  {self._one_line_doc(cls)}"
                        )
                    for method in cls.get("methods", []):
                        if method["name"].startswith("_"):
                            # 跳过私有方法（__init__ 除外不搜索展示）
                            continue
                        if self._match(query_lower, method):
                            results.append(
                                f"[{plat}] {module_name}.{cls['name']}.{method['name']}()\n"
                                f"  {self._one_line_doc(method)}"
                            )

        if not results:
            return f"未找到与 '{query}' 相关的 API。请尝试其他关键词。"

        header = f"搜索 '{query}' 共找到 {len(results)} 条结果：\n"
        # 限制返回数量，避免过长
        if len(results) > 30:
            return header + "\n".join(results[:30]) + f"\n\n... 还有 {len(results) - 30} 条结果，请缩小搜索范围。"
        return header + "\n".join(results)

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _fuzzy_match_modules(modules: list[dict], query: str) -> list[dict]:
        """模糊匹配模块名。

        匹配策略（按优先级）：
        1. 完全匹配
        2. 模块名以 query 结尾（如 query="screen" 匹配 "ascript.windows.screen"）
        3. 模块名包含 query
        """
        exact = [m for m in modules if m["module"].lower() == query]
        if exact:
            return exact

        endswith = [m for m in modules if m["module"].lower().endswith("." + query)]
        if endswith:
            return endswith

        contains = [m for m in modules if query in m["module"].lower()]
        return contains

    @staticmethod
    def _match(query: str, item: dict) -> bool:
        """判断一个函数/方法是否匹配搜索词。"""
        name = item.get("name", "").lower()
        doc = item.get("docstring", "").lower()
        return query in name or query in doc

    @staticmethod
    def _match_class(query: str, cls: dict) -> bool:
        """判断一个类是否匹配搜索词。"""
        name = cls.get("name", "").lower()
        doc = cls.get("docstring", "").lower()
        return query in name or query in doc

    @staticmethod
    def _one_line_doc(item: dict) -> str:
        """提取 docstring 的第一行。"""
        doc = item.get("docstring", "") or ""
        first = doc.split("\n")[0].strip()
        return first if first else "(无文档)"

    @staticmethod
    def _format_module(mod: dict) -> str:
        """将一个模块的完整 API 格式化为可读文本。"""
        lines: list[str] = []
        lines.append(f"# 模块: {mod['module']}")
        if mod.get("docstring"):
            lines.append(f"\n{mod['docstring']}\n")

        # 模块级函数
        functions = mod.get("functions", [])
        if functions:
            lines.append("## 函数\n")
            for func in functions:
                lines.append(_format_callable(func))

        # 类
        classes = mod.get("classes", [])
        if classes:
            lines.append("## 类\n")
            for cls in classes:
                lines.append(_format_class(cls))

        return "\n".join(lines)


# ------------------------------------------------------------------
# 格式化辅助函数
# ------------------------------------------------------------------

def _format_params(params: list[dict]) -> str:
    """将参数列表格式化为函数签名字符串。"""
    parts: list[str] = []
    for p in params:
        s = p["name"]
        if p.get("type"):
            s += f": {p['type']}"
        if p.get("default") is not None:
            s += f" = {p['default']}"
        parts.append(s)
    return ", ".join(parts)


def _format_callable(func: dict) -> str:
    """格式化一个函数/方法。"""
    params_str = _format_params(func.get("params", []))
    ret = func.get("return_type") or ""
    sig = f"  {func['name']}({params_str})"
    if ret:
        sig += f" -> {ret}"
    lines = [sig]
    if func.get("docstring"):
        # 缩进 docstring
        for line in func["docstring"].split("\n"):
            lines.append(f"    {line}")
    lines.append("")
    return "\n".join(lines)


def _format_class(cls: dict) -> str:
    """格式化一个类。"""
    bases = ", ".join(cls.get("bases", []))
    header = f"  class {cls['name']}"
    if bases:
        header += f"({bases})"
    lines = [header]
    if cls.get("docstring"):
        for line in cls["docstring"].split("\n"):
            lines.append(f"    {line}")
        lines.append("")

    # 类变量
    for cv in cls.get("class_variables", []):
        lines.append(f"    {cv['name']} = {cv.get('value', '...')}")
    if cls.get("class_variables"):
        lines.append("")

    # 方法
    for method in cls.get("methods", []):
        decorators = method.get("decorators", [])
        for dec in decorators:
            lines.append(f"    @{dec}")
        params_str = _format_params(method.get("params", []))
        ret = method.get("return_type") or ""
        sig = f"    {method['name']}({params_str})"
        if ret:
            sig += f" -> {ret}"
        lines.append(sig)
        if method.get("docstring"):
            for dline in method["docstring"].split("\n"):
                lines.append(f"      {dline}")
        lines.append("")

    return "\n".join(lines)


# 全局单例
api_store = ApiStore()
