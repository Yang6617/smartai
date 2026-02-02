from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RAGConfig:
    """
    RAG 引擎配置
    """
    # 向量库配置
    collection_name: str = "knowledge_base_chunks"
    vector_top_k: int = 8  # 增加检索数量以提高找到相关信息的概率
    similarity_threshold: float = 0.3  # 相似度阈值，低于此值的结果可能被忽略
    
    # LLM配置
    temperature: float = 0.3  # 稍微增加温度以提高响应多样性
    max_tokens: int = 1536  # 增加最大token数以允许更详细的回答
    
    # 检索配置
    rerank_enabled: bool = True  # 启用重排
    fusion_enabled: bool = False  # 启用多路融合
    hybrid_search_enabled: bool = False  # 启用混合搜索
    
    # 性能配置
    cache_enabled: bool = True  # 启用缓存
    cache_ttl_seconds: int = 300  # 缓存生存时间
    max_concurrent_requests: int = 10  # 最大并发请求数
    
    # 调试配置
    debug_mode: bool = True  # 启用调试模式以获取更多信息

    @classmethod
    def default(cls) -> RAGConfig:
        return cls()