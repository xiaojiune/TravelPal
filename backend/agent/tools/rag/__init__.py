"""RAG 工具子包：文档知识检索。

对应 TOOL_CATEGORIES 的 "rag" 分组。当前实现为 BM25 检索（service.py），
未来混合检索（BM25 + 向量）在此子包内扩展，tools 入口 search_rag 契约不变。
"""

from backend.agent.tools.rag.service import search_rag

__all__ = [
    "search_rag",
]
