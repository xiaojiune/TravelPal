"""从 __init__.py 的 from X import Y 语句自动生成 __all__。

用法:
    python -m backend.tools.sync_all

设计原则:
    - import 行是公开接口的唯一真实来源
    - 以下划线开头的名称不会被加入 __all__
    - 脚本不增加不减少导入，只生成 __all__
"""

import ast
import os

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================== AST 解析 ==================


def _collect_names(source: str) -> list[str]:
    """解析源码中所有 from X import Y 语句，收集公开名称。"""
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if not alias.name.startswith("_"):
                    names.append(alias.asname or alias.name)
    return names


# ================== __all__ 生成 ==================


def _rebuild(source: str, names: list[str]) -> str:
    """扫描 AST 找到最后一个 import 行，截断后追加 __all__ 列表。

    策略：丢弃 import 行之后的所有内容（已有 __all__ 或其他代码），
    从最后一个 import 行截断，在末尾生成新的 __all__ 块。
    自动检测原始换行符风格（LF / CRLF）并保持一致。

    Args:
        source: __init__.py 的原始源码。
        names: 需要加入 __all__ 的公开名称列表。

    Returns:
        str: 替换 __all__ 后的完整源码。
    """
    tree = ast.parse(source)

    import_linenos = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            import_linenos.add(node.lineno)

    if not import_linenos:
        return source

    last = max(import_linenos)
    source_lines = source.splitlines(keepends=True)
    eol = "\r\n" if source_lines and source_lines[0].endswith("\r\n") else "\n"

    result = source_lines[:last]
    while result and result[-1].strip() == "":
        result.pop()

    indent = "    "
    all_items = f"{eol}".join(f"{indent}{name!r}," for name in names)
    all_block = f"{eol}{eol}__all__ = [{eol}{all_items}{eol}]{eol}"

    result.append(all_block)
    return "".join(result)


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
