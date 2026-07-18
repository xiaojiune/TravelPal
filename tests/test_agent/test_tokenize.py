"""分词器 _tokenize() 单元测试。"""
from backend.agent.tools.rag import _tokenize


class TestTokenize:
    def test_chinese_chars(self):
        assert _tokenize("白云山") == ["白", "云", "山"]

    def test_mixed(self):
        tokens = _tokenize("BM25 检索引擎")
        assert "bm25" in tokens
        assert "检" in tokens

    def test_english_only(self):
        assert _tokenize("hello world") == ["hello", "world"]

    def test_empty(self):
        assert _tokenize("") == []

    def test_punctuation_ignored(self):
        tokens = _tokenize("部署-指引")
        assert "部署" not in tokens  # 不是单独的中文块
