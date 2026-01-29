from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class RAGConfig:
    """
    RAG 推理引擎统一配置

    建议：
    - 服务启动时构建一份 RAGConfig
    - 注入到 orchestrator / api / evaluator 中
    """

    # ===============================
    # 检索相关
    # ===============================
    collection_name: str = "knowledge_base_chunks"
    vector_top_k: int = 8
    enable_rerank: bool = False

    # ===============================
    # Prompt 相关
    # ===============================
    max_context_chunks: int = 8          # 最多使用多少个 chunk 进 prompt
    max_context_chars: int = 3000        # 上下文最大字符数
    require_citation: bool = True        # 是否强制引用

    # ===============================
    # LLM 相关
    # ===============================
    temperature: float = 0.2
    max_tokens: int = 1024
    stream_default: bool = False

    # ===============================
    # 稳定性 / 降级
    # ===============================
    allow_empty_context: bool = False    # 没有检索结果是否允许回答
    fallback_on_llm_error: bool = True

    # ===============================
    # 评估 / 调试
    # ===============================
    enable_debug: bool = True
    enable_evaluator: bool = False       # 是否启用回答质量评估

    # ===============================
    # 自定义扩展
    # ===============================
    extra: Dict[str, str] = field(default_factory=dict)
