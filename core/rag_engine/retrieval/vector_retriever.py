from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# 这里不硬依赖你们 core 包路径，避免后续目录调整时难改；
# 实际工程里你可以改为：from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy

from .filters import RetrievalFilter, build_where_filter, build_where_document_filter


@dataclass
class RetrievalHit:
    """
    统一的检索命中结构（后续 prompt_builder 直接消费）
    """
    id: str
    score: float                     # 越大越好（我们会把 distance 归一化成 score）
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None

    # 常用字段做一层便捷映射（可为空）
    document_id: Optional[str] = None
    chunk_index: Optional[int] = None
    source_info: Optional[str] = None
    source_type: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    uploader_id: Optional[str] = None


@dataclass
class VectorRetrieverConfig:
    """
    向量检索配置
    """
    top_k: int = 8
    include_embeddings: bool = False
    # distance -> score 的转换策略：
    # - chroma 默认 distances 一般是“越小越相似”（如 L2/余弦距离形式）
    # 我们用 score = 1 / (1 + distance) 做简单转化
    score_mode: str = "inverse_distance"


class VectorRetriever:
    """
    向量检索器：封装 VectorDBProxy.query_vectors + 结果标准化
    """

    def __init__(self, db_proxy: VectorDBProxy, config: Optional[VectorRetrieverConfig] = None) -> None:
        self.db_proxy = db_proxy
        self.config = config or VectorRetrieverConfig()

    def retrieve(
        self,
        collection_name: str,
        query_embedding: List[float],
        rf: Optional[RetrievalFilter] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievalHit]:
        """
        执行向量检索
        """
        k = int(top_k or self.config.top_k)
        rf = rf or RetrievalFilter()

        where = build_where_filter(rf)
        where_document = build_where_document_filter(rf)

        # 添加调试信息
        # print(f"[DEBUG] Vector Retriever - Querying collection: {collection_name}")
        # print(f"[DEBUG] Vector Retriever - Filter: {rf}")
        # print(f"[DEBUG] Vector Retriever - Where filter: {where}")
        # print(f"[DEBUG] Vector Retriever - Where document filter: {where_document}")

        # 这里直接调用你们的 proxy（其内部带稳定性重试/监控）
        results = self.db_proxy.query_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            n_results=k,
            where=where,
            where_document=where_document,
        )

        # print(f"[DEBUG] Vector Retriever - Query results count: {len(results) if results else 0}")

        hits: List[RetrievalHit] = []
        for r in results or []:
            hit = self._to_hit(r)
            if hit:
                hits.append(hit)

        # 按 score 降序（越大越相关）- 使用更高效的排序方法
        hits = sorted(hits, key=lambda x: x.score, reverse=True)
        
        # 确保返回指定数量的结果
        return hits[:k]

    def _to_hit(self, r: Dict[str, Any]) -> Optional[RetrievalHit]:
        """
        将 VectorDBProxy 的返回结果转换成 RetrievalHit

        你们 adapter 返回 dict keys: id/distance/metadata/document/embedding
        """
        _id = r.get("id")
        if not _id:
            return None

        distance = r.get("distance")
        score = self._distance_to_score(distance)

        md = r.get("metadata") or {}
        text = r.get("document")
        emb = r.get("embedding") if self.config.include_embeddings else None

        hit = RetrievalHit(
            id=str(_id),
            score=float(score),
            text=text,
            metadata=md,
            embedding=emb,
        )

        # 抽取常用字段（与 batch_processor / db_design 对齐）
        if isinstance(md, dict):
            hit.document_id = md.get("document_id")
            hit.chunk_index = md.get("chunk_index")
            hit.source_info = md.get("source_info")
            hit.source_type = md.get("source_type")
            hit.knowledge_base_id = md.get("knowledge_base_id")
            hit.uploader_id = md.get("uploader_id")

        return hit

    def _distance_to_score(self, distance: Any) -> float:
        """
        将 distance 转成“越大越好”的 score，便于融合/排序
        """
        if distance is None:
            return 0.0
        try:
            d = float(distance)
        except Exception:
            return 0.0

        mode = (self.config.score_mode or "").lower()
        if mode == "inverse_distance":
            return 1.0 / (1.0 + max(d, 0.0))
        if mode == "neg_distance":
            return -d
        # 默认 fallb
