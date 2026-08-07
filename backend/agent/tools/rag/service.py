"""RAG 检索工具：BM25 文档检索。

引擎（RagEngine）位于 infrastructure/retrieval/bm25.py，本模块仅提供
工具形态的全局接口，供 TOOL_REGISTRY 注册与 MCP 旁路暴露。
"""

from backend.infrastructure.retrieval.bm25 import get_engine


def search_rag(query: str, k: int = 3) -> list[dict]:
    """全局接口：检索 RAG 文档库，惰性初始化。

    Args:
        query: 用户查询文本。
        k: 返回 top-k 条结果，默认 3。

    Returns:
        list[dict]: 每项含 score/source/heading/text，按 BM25 分数降序。
    """
    return get_engine().search(query, k)
