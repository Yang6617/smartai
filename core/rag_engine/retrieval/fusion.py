from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .vector_retriever import RetrievalHit


@dataclass
class FusionConfig:
    weight_vector: float = 1.0
    weight_keyword: float = 0.3
    top_k: int = 8


def _dedupe_key(hit: RetrievalHit) -> str:
    if hit.document_id is not None and hit.chunk_index is not None:
        return f"{hit.document_id}::chunk::{hit.chunk_index}"
    return f"id::{hit.id}"


def _minmax_norm(scores: List[float]) -> List[float]:
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mx - mn < 1e-9:
        return [1.0 for _ in scores]
    return [(s - mn) / (mx - mn) for s in scores]


def fuse_hits(
    vector_hits: List[RetrievalHit],
    keyword_hits: List[RetrievalHit],
    cfg: FusionConfig,
) -> List[RetrievalHit]:
    """
    将两路 hits 融合为一路（返回按融合分排序后的 hits）
    """
    # 归一化各自分数，避免量纲不同
    v_scores = _minmax_norm([h.score for h in vector_hits])
    k_scores = _minmax_norm([h.score for h in keyword_hits])

    v_map: Dict[str, Tuple[RetrievalHit, float]] = {}
    for h, ns in zip(vector_hits, v_scores):
        v_map[_dedupe_key(h)] = (h, ns)

    k_map: Dict[str, Tuple[RetrievalHit, float]] = {}
    for h, ns in zip(keyword_hits, k_scores):
        k_map[_dedupe_key(h)] = (h, ns)

    keys = set(v_map.keys()) | set(k_map.keys())
    merged: List[RetrievalHit] = []

    for key in keys:
        v = v_map.get(key)
        k = k_map.get(key)

        if v and k:
            # 两路都命中：融合分
            base_hit = v[0]
            fused_score = cfg.weight_vector * v[1] + cfg.weight_keyword * k[1]
            base_hit.score = float(fused_score)
            # 可选：把 keyword 的信息并入 metadata（避免丢信号）
            if base_hit.metadata is None:
                base_hit.metadata = {}
            base_hit.metadata["fusion"] = {"vector": v[1], "keyword": k[1]}
            merged.append(base_hit)
        elif v:
            base_hit = v[0]
            base_hit.score = float(cfg.weight_vector * v[1])
            if base_hit.metadata is None:
                base_hit.metadata = {}
            base_hit.metadata["fusion"] = {"vector": v[1], "keyword": 0.0}
            merged.append(base_hit)
        else:
            base_hit = k[0]
            base_hit.score = float(cfg.weight_keyword * k[1])
            if base_hit.metadata is None:
                base_hit.metadata = {}
            base_hit.metadata["fusion"] = {"vector": 0.0, "keyword": k[1]}
            merged.append(base_hit)

    merged.sort(key=lambda x: x.score, reverse=True)
    return merged[: cfg.top_k]
