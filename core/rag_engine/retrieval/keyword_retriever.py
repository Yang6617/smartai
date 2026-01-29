from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .vector_retriever import RetrievalHit


@dataclass
class KeywordRetrieverConfig:
    top_k: int = 8


class KeywordRetriever:
    """
    关键词检索器（占位）

    生产建议：
    - 接入 ES/OpenSearch
    - 或者本地 BM25 倒排（需要持久化索引）
    """

    def __init__(self, config: Optional[KeywordRetrieverConfig] = None) -> None:
        self.config = config or KeywordRetrieverConfig()

    def retrieve(self, query: str, corpus: List[str], top_k: Optional[int] = None) -> List[RetrievalHit]:
        """
        极简关键词检索：按命中次数排序
        """
        k = int(top_k or self.config.top_k)
        q = (query or "").strip()
        if not q:
            return []

        terms = [t for t in q.replace(",", " ").replace("，", " ").split() if t]
        if not terms:
            return []

        scored = []
        for idx, text in enumerate(corpus):
            if not text:
                continue
            score = 0
            lower = text.lower()
            for t in terms:
                score += lower.count(t.lower())
            if score > 0:
                scored.append((idx, score, text))

        scored.sort(key=lambda x: x[1], reverse=True)
        hits: List[RetrievalHit] = []
        for idx, score, text in scored[:k]:
            hits.append(
                RetrievalHit(
                    id=f"kw_{idx}",
                    score=float(score),
                    text=text,
                    metadata={"source_type": "keyword_corpus", "chunk_index": idx},
                )
            )
        return hits
