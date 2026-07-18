"""RAG 检索引擎：BM25 全文检索，零外部依赖。

扫描 docs/*.md + README.md，按 ## 标题切块后建立 BM25 索引。
分词策略：英文按空白拆分，中文单字索引，不依赖 jieba 等分词库。
"""

import os
import math
import re
from collections import Counter, defaultdict

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DOC_DIR = os.path.join(_PROJECT_ROOT, "docs")


def _tokenize(text: str) -> list[str]:
    """中英文混合分词：英文按空白分割，中文拆为单字。"""
    tokens = []
    for part in re.split(r'([\u4e00-\u9fff]+)', text):
        if not part:
            continue
        if re.match(r'^[\u4e00-\u9fff]+$', part):
            tokens.extend(list(part))
        else:
            tokens.extend(part.lower().split())
    return [t for t in tokens if t.strip()]


class RagEngine:
    """零依赖 BM25 检索引擎，惰性初始化。"""

    def __init__(self):
        self._docs: list[dict] = []
        self._avgdl = 0.0
        self._idf: dict[str, float] = {}
        self._initialized = False

    def init(self) -> None:
        if self._initialized:
            return
        self._load_docs()
        self._build_index()
        self._initialized = True

    def _load_docs(self) -> None:
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
            raw_sections = re.split(r'(?=^## )', content, flags=re.MULTILINE)
            for sec in raw_sections:
                sec = sec.strip()
                if not sec:
                    continue
                lines = sec.split("\n")
                heading = lines[0].strip().lstrip("#").strip()
                body_lines = [l for l in lines[1:] if not l.startswith("```")]
                body = "\n".join(body_lines).strip()
                if not body:
                    continue
                tokens = _tokenize(f"{heading}\n{body}")
                if not tokens:
                    continue
                doc_id = f"{rel}#{heading}" if heading else rel
                self._docs.append({
                    "id": doc_id, "source": rel, "heading": heading,
                    "text": f"{heading}\n{body}", "tokens": tokens,
                    "_tf": Counter(tokens),
                })

    def _build_index(self) -> None:
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

    def search(self, query: str, k: int = 3) -> list[dict]:
        """BM25 检索，返回 top-k 条结果。"""
        if not self._initialized:
            self.init()
        if not self._docs:
            return []
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

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
        return [
            {"score": round(s, 4), "source": d["source"],
             "heading": d["heading"], "text": d["text"][:300]}
            for s, d in results[:k]
        ]


_engine = RagEngine()


def search_rag(query: str, k: int = 3) -> list[dict]:
    """全局接口：检索 RAG 文档库，惰性初始化。"""
    return _engine.search(query, k)
