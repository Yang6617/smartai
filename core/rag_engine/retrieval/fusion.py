from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import copy
from core.rag_engine.retrieval.vector_retriever import RetrievalHit


@dataclass
class FusionConfig:
    """
        RRF 融合配置
        """
    top_k: int = 8
    rrf_k: int = 60
    weight_vector: float = 1.0
    weight_keyword: float = 0.8


def _dedupe_key(hit: RetrievalHit) -> str:
    """
       用统一主键做去重：
       优先 document_id + chunk_index
       否则 fallback 到 id
       """
    if hit.document_id is not None and hit.chunk_index is not None:
        return f"{hit.document_id}::chunk::{hit.chunk_index}"
    return f"id::{hit.id}"


def _clone_hit(hit: RetrievalHit) -> RetrievalHit:
    """
    避免直接修改原始 hits，减少副作用
    """
    cloned = copy.copy(hit)
    cloned.metadata = dict(hit.metadata or {})
    return cloned


def fuse_hits(
    vector_hits: List[RetrievalHit],
    keyword_hits: List[RetrievalHit],
    cfg: FusionConfig,
) -> List[RetrievalHit]:
    """
    使用 RRF（Reciprocal Rank Fusion）融合两路召回结果。

    score = sum(weight / (rrf_k + rank))

    说明：
    - rank 从 1 开始
    - 不依赖原始 score 尺度
    - 更适合 vector + BM25 混合检索
    """
    merged: Dict[str, RetrievalHit] = {}
    rrf_scores: Dict[str, float] = {}
    debug_info: Dict[str, Dict[str, float]] = {}

    # 向量召回
    for rank, hit in enumerate(vector_hits, start=1):
        key = _dedupe_key(hit)
        if key not in merged:
            merged[key] = _clone_hit(hit)

        contribution = cfg.weight_vector * (1.0 / (cfg.rrf_k + rank))
        rrf_scores[key] = rrf_scores.get(key, 0.0) + contribution

        if key not in debug_info:
            debug_info[key] = {"vector": 0.0, "keyword": 0.0}
        debug_info[key]["vector"] = contribution

    # 关键词召回
    for rank, hit in enumerate(keyword_hits, start=1):
        key = _dedupe_key(hit)
        if key not in merged:
            merged[key] = _clone_hit(hit)

        contribution = cfg.weight_keyword * (1.0 / (cfg.rrf_k + rank))
        rrf_scores[key] = rrf_scores.get(key, 0.0) + contribution

        if key not in debug_info:
            debug_info[key] = {"vector": 0.0, "keyword": 0.0}
        debug_info[key]["keyword"] = contribution

    results: List[RetrievalHit] = []
    for key, hit in merged.items():
        hit.score = float(rrf_scores[key])
        hit.retriever = "fusion"

        if hit.metadata is None:
            hit.metadata = {}

        hit.metadata["fusion"] = {
            "method": "rrf",
            "score": rrf_scores[key],
            "vector": debug_info[key]["vector"],
            "keyword": debug_info[key]["keyword"],
        }

        results.append(hit)

    results.sort(key=lambda x: x.score, reverse=True)

    # 给调试更直观一点的 rank
    for idx, hit in enumerate(results, start=1):
        try:
            hit.rank = idx
        except Exception:
            pass

    return results[: cfg.top_k]
