"""从 __init__.py 的 from X import Y 语句自动生成 __all__。

用法:
    python -m backend.utils.sync_all

设计原则:
    - import 行是公开接口的唯一真实来源
    - 以下划线开头的名称不会被加入 __all__
    - 脚本不增加不减少导入，只生成 __all__
"""

import ast
import os

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================== AST 解析 ==================

_COLLECT_EXCLUDE = frozenset({"Callable"})

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _collect_names(source: str) -> list[str]:
    """解析源码中所有 from X import Y 语句和顶层 __all__ 兼容变量，收集公开名称。"""
    tree = ast.parse(source)
    names = []

    # 从 import 语句收集
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if not name.startswith("_") and name not in _COLLECT_EXCLUDE:
                    names.append(name)

    # 从 __all__ 列表中收集（保留原手动添加的非 import 名称）
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                val = elt.value
                                if val not in names and not val.startswith("_") and val not in _COLLECT_EXCLUDE:
                                    names.append(val)
    return names


# ================== __all__ 生成 ==================


def _rebuild(source: str, names: list[str]) -> str:
    """替换已有 __all__ 块，若不存在则在末尾追加（不破坏其他代码）。

    Args:
        source: __init__.py 的原始源码。
        names: 需要加入 __all__ 的公开名称列表。

    Returns:
        str: 替换 __all__ 后的完整源码。
    """
    tree = ast.parse(source)
    source_lines = source.splitlines(keepends=True)
    eol = "\r\n" if source_lines and source_lines[0].endswith("\r\n") else "\n"

    indent = "    "
    all_items = f"{eol}".join(f"{indent}{name!r}," for name in names)
    all_block = f"__all__ = [{eol}{all_items}{eol}]{eol}"

    # 查找已有的 __all__ 赋值节点
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    start = node.lineno - 1
                    end = node.end_lineno if node.end_lineno is not None else node.lineno
                    result = source_lines[:start] + [all_block] + source_lines[end:]
                    return "".join(result)

    # 不存在 __all__：在文件末尾追加
    while source_lines and source_lines[-1].strip() == "":
        source_lines.pop()
    source_lines.append(eol)
    source_lines.append(all_block)
    return "".join(source_lines)


# ================== 文件写入 ==================


def sync_file(path: str) -> bool:
    """对单个 __init__.py 执行同步：解析 import 行 → 生成 __all__ → 写回文件。

    Args:
        path: __init__.py 的绝对路径。

    Returns:
        bool: True 表示文件已被修改，False 表示无需变更。
    """
    with open(path, encoding="utf-8", newline="") as f:
        source = f.read()

    names = _collect_names(source)
    if not names:
        return False

    new_source = _rebuild(source, names)
    if new_source == source:
        return False

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new_source)
    return True


# ================== CLI 入口 ==================


def main():
    """扫描 backend/ 下所有 __init__.py，同步 __all__ 后输出变更清单。"""
    changed = []
    for root, _dirs, files in os.walk(BACKEND):
        if "__init__.py" in files:
            path = os.path.join(root, "__init__.py")
            if sync_file(path):
                changed.append(os.path.relpath(path, BACKEND))

    if changed:
        print("同步 __all__ 完成：")
        for p in changed:
            print(f"  {p}")
    else:
        print("所有文件已最新，无需修改。")


if __name__ == "__main__":
    main()
