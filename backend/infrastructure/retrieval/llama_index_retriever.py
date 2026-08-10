"""LlamaIndex 检索实现占位。

LlamaIndex 用于增强 RAG（当前 BM25 见 backend/infrastructure/retrieval/bm25.py）。
当前仅保留目录占位（ADR-008 轴7），具体实现统一 TODO，按需引入。
"""


class LlamaIndexRetriever:
    """LlamaIndex 检索器（占位，未实现）。"""

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """向量检索相关文档片段（TODO 占位）。

        Args:
            query: 查询文本。
            k: 返回条数。

        Returns:
            检索结果列表（当前未实现）。

        Raises:
            NotImplementedError: 占位方法，未实现。
        """
        # TODO: 引入 llama-index 后实现向量检索（与 BM25 并行，候选做混合排序）
        raise NotImplementedError
