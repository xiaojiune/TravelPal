"""RAG 引擎 RagEngine 单元测试。"""

from backend.agent.tools.rag import RagEngine


class TestRagEngine:
    def test_initial_attrs_defined(self):
        """关键实例属性应在 __init__ 中初始化，避免空索引时 AttributeError。"""
        engine = RagEngine()
        assert engine._docs == []
        assert engine._idf == {}
        assert engine._initialized is False

    def test_build_index_empty_docs(self):
        """空文档列表时 _build_index() 不应抛异常（回归 _docs 未初始化 bug）。"""
        engine = RagEngine()
        engine._docs = []
        engine._build_index()
        assert engine._avgdl == 0.0

    def test_init_idempotent(self):
        """init() 幂等：多次调用仅初始化一次。"""
        engine = RagEngine()
        engine.init()
        engine.init()
        assert engine._initialized is True

    def test_search_returns_after_init(self):
        """search() 惰性初始化后应返回结构正确的结果列表（真实文档库）。"""
        engine = RagEngine()
        results = engine.search("检索引擎")
        assert isinstance(results, list)
        assert results[0]["score"] > 0
        assert "source" in results[0]
