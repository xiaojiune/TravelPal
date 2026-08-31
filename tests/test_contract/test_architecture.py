"""六边形（整洁）架构依赖方向守护测试。

锁定 backend 跨层 import 方向不被回退破坏：
- domain 不依赖 infrastructure / 应用层（api/tasks/agent/mcp/observability）。
- infrastructure 不依赖应用层。

后续演进（如接入层进一步归位）若意外出现反向 import，本测试立即失败并告警，
把「架构依赖」固化为可持续验证的契约，而非仅靠口头约定。
"""

from backend.utils.architecture import check_hexagonal_layering


def test_hexagonal_layering_direction():
    """domain/infrastructure 不得反向依赖实现/应用层，否则失败并列出违规点。"""
    result = check_hexagonal_layering()
    assert result["ok"], "六边形依赖违规:\n" + "\n".join(
        f"  {v['file']}:{v['line']}  {v['src_layer']} -> {v['target_layer']}  ({v['import_str']})"
        for v in result["violations"]
    )
