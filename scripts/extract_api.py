"""
从 ascript 源码中提取 API 文档，生成 JSON 数据供 MCP 服务使用。
使用 Python ast 模块解析源码，提取类、方法、函数的签名和 docstring。
"""
import ast
import json
import os
import sys
from pathlib import Path
from typing import Any


def extract_param_info(node: ast.FunctionDef) -> list[dict]:
    """从函数定义节点中提取参数信息。"""
    params = []
    args = node.args

    # 所有普通参数
    all_args = args.args
    # 默认值（从后往前对齐）
    defaults = args.defaults
    num_defaults = len(defaults)
    num_args = len(all_args)

    for i, arg in enumerate(all_args):
        if arg.arg == 'self' or arg.arg == 'cls':
            continue

        param = {"name": arg.arg}

        # 类型注解
        if arg.annotation:
            param["type"] = ast.unparse(arg.annotation)

        # 默认值
        default_index = i - (num_args - num_defaults)
        if default_index >= 0:
            try:
                param["default"] = ast.unparse(defaults[default_index])
            except Exception:
                param["default"] = "..."

        params.append(param)

    # *args
    if args.vararg:
        p = {"name": f"*{args.vararg.arg}"}
        if args.vararg.annotation:
            p["type"] = ast.unparse(args.vararg.annotation)
        params.append(p)

    # **kwargs
    if args.kwarg:
        p = {"name": f"**{args.kwarg.arg}"}
        if args.kwarg.annotation:
            p["type"] = ast.unparse(args.kwarg.annotation)
        params.append(p)

    return params


def extract_return_type(node: ast.FunctionDef) -> str | None:
    """提取函数返回类型注解。"""
    if node.returns:
        return ast.unparse(node.returns)
    return None


def extract_function(node: ast.FunctionDef) -> dict:
    """提取函数/方法信息。"""
    info = {
        "name": node.name,
        "docstring": ast.get_docstring(node) or "",
        "params": extract_param_info(node),
        "return_type": extract_return_type(node),
        "decorators": [],
    }

    for dec in node.decorator_list:
        try:
            info["decorators"].append(ast.unparse(dec))
        except Exception:
            pass

    return info


def extract_class(node: ast.ClassDef) -> dict:
    """提取类信息，包括其方法。"""
    info = {
        "name": node.name,
        "docstring": ast.get_docstring(node) or "",
        "bases": [],
        "methods": [],
        "class_variables": [],
    }

    for base in node.bases:
        try:
            info["bases"].append(ast.unparse(base))
        except Exception:
            pass

    for item in ast.iter_child_nodes(node):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 跳过双下划线魔术方法（保留 __init__）
            if item.name.startswith('__') and item.name.endswith('__') and item.name != '__init__':
                continue
            info["methods"].append(extract_function(item))
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    var = {"name": target.id}
                    try:
                        var["value"] = ast.unparse(item.value)
                    except Exception:
                        pass
                    info["class_variables"].append(var)

    return info


def extract_module(file_path: str, rel_path: str) -> dict | None:
    """提取整个模块的 API 信息。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return None

    if not source.strip():
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    module_doc = ast.get_docstring(tree) or ""
    classes = []
    functions = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            cls_info = extract_class(node)
            if cls_info["methods"] or cls_info["docstring"] or cls_info["class_variables"]:
                classes.append(cls_info)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 跳过私有辅助函数（以_开头但非__init__）
            if not node.name.startswith('_'):
                functions.append(extract_function(node))

    if not classes and not functions and not module_doc:
        return None

    # 将文件路径转为模块路径
    module_path = rel_path.replace(os.sep, '/').replace('/', '.').removesuffix('.py')
    if module_path.endswith('.__init__'):
        module_path = module_path.removesuffix('.__init__')

    return {
        "module": module_path,
        "file": rel_path.replace(os.sep, '/'),
        "docstring": module_doc,
        "classes": classes,
        "functions": functions,
    }


def extract_platform(source_root: str, platform: str, sub_dirs: list[str]) -> dict:
    """提取一个平台下所有模块的 API。"""
    modules = []

    for sub_dir in sub_dirs:
        dir_path = os.path.join(source_root, sub_dir)
        if not os.path.isdir(dir_path):
            continue

        for root, dirs, files in os.walk(dir_path):
            # 跳过 __pycache__、license_source
            dirs[:] = [d for d in dirs if d != '__pycache__' and d != 'license_source' and d != 'android']

            for fname in sorted(files):
                if not fname.endswith('.py'):
                    continue

                file_path = os.path.join(root, fname)
                rel_path = os.path.relpath(file_path, source_root)
                module_info = extract_module(file_path, rel_path)
                if module_info:
                    modules.append(module_info)

    return {
        "platform": platform,
        "modules": modules,
    }


def main():
    # ascript 源码根目录
    if len(sys.argv) > 1:
        source_root = sys.argv[1]
    else:
        source_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ascript-windows'))

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/ascript_mcp/api_data'))
    os.makedirs(output_dir, exist_ok=True)

    platforms = {
        "android": ["ascript/android"],
        "ios": ["ascript/ios"],
        "windows": ["ascript/windows"],
    }

    for platform, dirs in platforms.items():
        print(f"提取 {platform} API...")
        data = extract_platform(source_root, platform, dirs)
        output_file = os.path.join(output_dir, f"{platform}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  -> {output_file} ({len(data['modules'])} 个模块)")

    print("完成！")


if __name__ == '__main__':
    main()
