"""DSPy prompt 优化占位。

DSPy（Declarative Self-improving Language Programs）用于 prompt 自动编译与优化。
当前仅保留目录占位（ADR-008 轴7），具体实现统一 TODO，按需引入，不提前依赖。
"""


class DSPyOptimizer:
    """DSPy prompt 优化器（占位，未实现）。"""

    def optimize(self, prompt: str) -> str:
        """优化 prompt（TODO 占位）。

        Args:
            prompt: 原始 prompt 文本。

        Returns:
            优化后的 prompt（当前未实现）。

        Raises:
            NotImplementedError: 占位方法，未实现。
        """
        # TODO: 引入 dspy 后实现 prompt 编译与优化（与 LLMService 防腐层解耦）
        raise NotImplementedError
