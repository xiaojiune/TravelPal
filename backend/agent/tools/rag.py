"""RAG 检索引擎：BM25 全文检索。

扫描 docs/*.md + README.md，按 ## 标题切块后建立 BM25 索引。
分词策略：中文用 jieba 分词，英文按空白拆分。
"""

import math
import os
import re
from collections import Counter, defaultdict

import jieba

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DOC_DIR = os.path.join(_PROJECT_ROOT, "docs")

_STOP_WORDS = frozenset(
    {
        "的",
        "了",
        "是",
        "在",
        "和",
        "与",
        "也",
        "就",
        "都",
        "而",
        "及",
        "或",
        "这",
        "那",
        "哪",
        "一",
        "不",
        "很",
        "会",
        "可以",
        "什么",
        "怎么",
        "如何",
        "为什么",
        "哪个",
        "哪些",
        "好吗",
        "吗",
        "呢",
        "吧",
        "啊",
        "哦",
        "嗯",
        "哈",
        "呀",
        "嘛",
        "我",
        "你",
        "他",
        "她",
        "它",
        "我们",
        "你们",
        "他们",
        "有",
        "要",
        "来",
        "去",
        "把",
        "被",
        "让",
        "给",
        "对",
        "从",
        "到",
        "上",
        "下",
        "中",
        "里",
        "外",
        "前",
        "后",
        "个",
        "种",
    }
)


def _tokenize(text: str) -> list[str]:
    """中英文混合分词：中文用 jieba，英文按空白分割，过滤停用词。"""
    tokens = []
    for part in re.split(r"([\u4e00-\u9fff]+)", text):
        if not part:
            continue
        if re.match(r"^[\u4e00-\u9fff]+$", part):
            tokens.extend(jieba.lcut(part))
        else:
            tokens.extend(part.lower().split())
    return [t for t in tokens if t.strip() and t not in _STOP_WORDS]


class RagEngine:
    """零依赖 BM25 检索引擎，惰性初始化。"""

    def __init__(self):
        self._docs: list[dict] = []
        self._avgdl = 0.0
        self._idf: dict[str, float] = {}
        self._initialized = False

    def init(self) -> None:
        """惰性初始化：扫描文档 → 切块 → 建立 BM25 索引。幂等，多次调用仅执行一次。"""
        if self._initialized:
            return
        self._load_docs()
        self._build_index()
        self._initialized = True

    def _load_docs(self) -> None:
        """扫描 docs/*.md + README.md，按 ## 标题切块后存入 self._docs。"""
        md_files = []
        if os.path.isdir(_DOC_DIR):
            for root, _, files in os.walk(_DOC_DIR):
                for f in files:
                    if f.endswith(".md"):
                        md_files.append(os.path.join(root, f))
        readme = os.path.join(_PROJECT_ROOT, "README.md")
        if os.path.isfile(readme):
            md_files.append(readme)

        for fp in sorted(md_files):
            rel = os.path.relpath(fp, _PROJECT_ROOT)
            try:
                with open(fp, encoding="utf-8") as fh:
                    content = fh.read()
            except Exception:
                continue
            raw_sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
            for sec in raw_sections:
                sec = sec.strip()
                if not sec:
                    continue
                lines = sec.split("\n")
                heading = lines[0].strip().lstrip("#").strip()
                body_lines = [line for line in lines[1:] if not line.startswith("```")]
                body = "\n".join(body_lines).strip()
                if not body:
                    continue
                tokens = _tokenize(f"{heading}\n{body}")
                if not tokens:
                    continue
                doc_id = f"{rel}#{heading}" if heading else rel
                self._docs.append(
                    {
                        "id": doc_id,
                        "source": rel,
                        "heading": heading,
                        "text": f"{heading}\n{body}",
                        "tokens": tokens,
                        "_tf": Counter(tokens),
                    }
                )

    def _build_index(self) -> None:
        """计算文档平均长度 + 每个词的 IDF，供 BM25 打分使用。"""
        n = len(self._docs)
        if n == 0:
            return
        self._avgdl = sum(len(d["tokens"]) for d in self._docs) / n
        df: dict[str, int] = defaultdict(int)
        for d in self._docs:
            for term in set(d["tokens"]):
                df[term] += 1
        for term, count in df.items():
            self._idf[term] = math.log((n - count + 0.5) / (count + 0.5) + 1.0)

    def _bm25_score(self, q_tokens: list[str]) -> list[tuple[float, dict]]:
        """计算 BM25 分数（k1=1.5, b=0.75），返回 (分数, 文档) 列表，按分数降序排列。"""
        k1, b = 1.5, 0.75
        results = []
        for d in self._docs:
            score = 0.0
            dl = len(d["tokens"])
            for term in set(q_tokens):
                tf = d["_tf"].get(term, 0)
                idf = self._idf.get(term, 0.0)
                if idf == 0.0:
                    continue
                score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / self._avgdl))
            if score > 0:
                results.append((score, d))
        results.sort(key=lambda x: -x[0])
        return results

    def search(self, query: str, k: int = 3) -> list[dict]:
        """BM25 检索，返回 top-k 条结果。低分时自动提取关键词重试。"""
        if not self._initialized:
            self.init()
        if not self._docs:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        results = self._bm25_score(q_tokens)
        if results and results[0][0] > 0.5:
            return [
                {"score": round(s, 4), "source": d["source"], "heading": d["heading"], "text": d["text"][:300]}
                for s, d in results[:k]
            ]
        keywords = [t for t in q_tokens if len(t) > 1]
        if keywords and keywords != q_tokens:
            results = self._bm25_score(keywords)
        return [
            {"score": round(s, 4), "source": d["source"], "heading": d["heading"], "text": d["text"][:300]}
            for s, d in results[:k]
        ]


_engine = RagEngine()


def search_rag(query: str, k: int = 3) -> list[dict]:
    """全局接口：检索 RAG 文档库，惰性初始化。

    Args:
        query: 用户查询文本。
        k: 返回 top-k 条结果，默认 3。

    Returns:
        list[dict]: 每项含 score/source/heading/text，按 BM25 分数降序。
    """
    return _engine.search(query, k)
