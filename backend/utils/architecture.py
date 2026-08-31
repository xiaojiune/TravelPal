"""六边形架构依赖校验：扫描 backend 跨层 import，检查依赖方向符合 domain/infra 分层。

TravelPal 后端收拢为六边形（整洁）架构：
- domain：端口（ports.py）+ 核心编排 + 纯算法，零外部实现依赖。
- infrastructure：端口实现（data/engine/llm/weather/retrieval/session），只依赖 domain。
- 应用/接入层：api/tasks/agent/mcp（消费 domain 端口，向下依赖）。
- utils/observability/config/typedefs：跨层通用纯工具 / 旁路指标 / 叶子模块，
  允许被任意层依赖（observability 供各层上报指标，见 infra/api/tasks 的引用）。

硬规则（违规即失败）：
- domain 不允许依赖 infrastructure / api / agent / tasks / mcp。
- infrastructure 不允许依赖 api / agent / tasks / mcp。
- utils/observability/config/typedefs 视为「工具 / 旁路 / 叶子」，默认不计入违规；
  strict=True 时额外查 domain → utils（把工具也挡在 domain 外）。

说明: 仅识别绝对导入 `backend.<layer>`（跨层主要形态）；相对导入视为层内，
默认不计。若未来出现跨层相对导入，值此补扩。

示例:
    from backend.utils.architecture import check_hexagonal_layering
    result = check_hexagonal_layering()
    assert result["ok"]
"""

import ast
import os
from pathlib import Path

# 硬规则：src 层不得依赖 target 应用/实现层（utils/config/typedefs 另由 strict/叶子处理）。
_FORBIDDEN: dict[str, set[str]] = {
    "domain": {"infrastructure", "api", "agent", "tasks", "mcp"},
    "infrastructure": {"api", "agent", "tasks", "mcp"},
}


def _top_layer(module: str) -> str | None:
    """取 `backend.<layer>...` 的 `<layer>`；非 backend 前缀或文件级模块返回 None。"""
    parts = module.split(".")
    if parts and parts[0] == "backend" and len(parts) > 1:
        return parts[1]
    return None


def _src_layer(rel: Path) -> str:
    """取相对于 backend/ 的顶层段（backend/agent/planning/x.py → agent）。"""
    return rel.parts[0] if rel.parts else ""


def check_hexagonal_layering(project_root: str | Path | None = None, strict: bool = False) -> dict:
    """扫描 backend 各 .py 的跨层 import，返回依赖方向校验结果。

    Args:
        project_root: 项目根目录（含 backend/）。默认取本文件上两级。
        strict: True 时 domain 额外不得依赖 utils（默认 False，utils 视为工具层）。

    Returns:
        dict: {
            ok: bool（violations 为空则 True）,
            violations: list[{file, line, src_layer, target_layer, import_str}],
            edges: list[tuple[str, str]]（去重后的跨层边）,
            project_root: str,
        }
    """
    project_root = Path(project_root) if project_root else Path(__file__).resolve().parent.parent.parent
    backend_root = project_root / "backend"
    violations: list[dict] = []
    edges: set[tuple[str, str]] = set()

    for dirpath, _, files in os.walk(backend_root):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = Path(dirpath) / fn
            rel = path.relative_to(backend_root)
            src_layer = _src_layer(rel)
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    # 相对导入（from . import xxx）视为层内，不计
                    if node.module:
                        targets = [node.module]
                    else:
                        continue
                for mod in targets:
                    tgt = _top_layer(mod)
                    if tgt is None:
                        continue
                    edges.add((src_layer, tgt))
                    is_violation = tgt in _FORBIDDEN.get(src_layer, set())
                    if is_violation or (strict and src_layer == "domain" and tgt == "utils"):
                        violations.append(
                            {
                                "file": str(rel),
                                "line": getattr(node, "lineno", 0),
                                "src_layer": src_layer,
                                "target_layer": tgt,
                                "import_str": mod,
                            }
                        )

    return {
        "ok": not violations,
        "violations": violations,
        "edges": sorted(edges),
        "project_root": str(project_root),
    }
