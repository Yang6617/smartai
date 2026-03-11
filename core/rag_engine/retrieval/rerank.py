from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from core.rag_engine.retrieval.vector_retriever import RetrievalHit


@dataclass
class RerankConfig:
    enabled: bool = False
    top_k: int = 8


class Reranker:
    """
    重排器（占位）

    可选实现：
    - Cross-Encoder（如 bge-reranker）
    - LLM rerank（成本更高）
    """

    def __init__(self, config: Optional[RerankConfig] = None) -> None:
        self.config = config or RerankConfig()

    def rerank(self, query: str, hits: List[RetrievalHit]) -> List[RetrievalHit]:
        """
        如果 enabled=False：直接返回原 hits
        """
        if not self.config.enabled:
            return hits[: self.config.top_k]
        # 占位：未来在这里调用 reranker 模型重排
        # 现在先按原 score 排序返回
        hits_sorted = sorted(hits, key=lambda x: x.score, reverse=True)
        return hits_sorted[: self.config.top_k]
