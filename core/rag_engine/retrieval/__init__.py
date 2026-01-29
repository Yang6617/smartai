"""
检索层（Retrieval）

能力：
- 向量检索（VectorDBProxy）
- 关键词检索（占位/可扩展）
- 过滤器构造（where/where_document）
- 结果融合（fusion）
- 可选重排（rerank）
"""

from .filters import RetrievalFilter, build_where_filter, build_where_document_filter
from .vector_retriever import VectorRetriever, VectorRetrieverConfig, RetrievalHit
from .keyword_retriever import KeywordRetriever, KeywordRetrieverConfig
from .fusion import FusionConfig, fuse_hits
from .rerank import Reranker, RerankConfig

__all__ = [
    "RetrievalFilter",
    "build_where_filter",
    "build_where_document_filter",
    "RetrievalHit",
    "VectorRetrieverConfig",
    "VectorRetriever",
    "KeywordRetrieverConfig",
    "KeywordRetriever",
    "FusionConfig",
    "fuse_hits",
    "RerankConfig",
    "Reranker",
]
