"""混合检索器占位。

融合 BM25 稀疏检索与向量稠密检索的混合打分策略，用于提升 RAG 召回质量。
当前仅保留目录占位（ADR-008 轴7），具体实现统一 TODO，按需引入。
"""


class HybridRetriever:
    """混合检索器（占位，未实现）。"""

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """混合检索相关文档片段（TODO 占位）。

        Args:
            query: 查询文本。
            k: 返回条数。

        Returns:
            检索结果列表（当前未实现）。

        Raises:
            NotImplementedError: 占位方法，未实现。
        """
        # TODO: 引入向量检索后融合 BM25 实现混合打分（RRF / 加权归一）
        raise NotImplementedError
