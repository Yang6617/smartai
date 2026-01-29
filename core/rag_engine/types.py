from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =========================================================
# 基础类型
# =========================================================

@dataclass
class Citation:
    """
    引用信息（回答中使用的资料来源）

    一条 Citation 通常对应一个向量 chunk
    """
    index: int                         # 引用编号（从 1 开始，对应 prompt 中的 [1][2]）
    document_id: Optional[str] = None  # 文档 ID
    chunk_index: Optional[int] = None  # chunk 在文档中的序号
    source_info: Optional[str] = None  # 原始来源信息（文件路径 / URL / 标题等）
    knowledge_base_id: Optional[str] = None  # 知识库 ID（如 team_id）


@dataclass
class RetrievalChunk:
    """
    检索得到的最小知识单元（向量 chunk）
    """
    id: str                            # 向量 ID
    text: str                          # chunk 原文内容
    score: float                       # 相关度得分（越大越相关）
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 常用字段直接拉平（方便下游使用）
    document_id: Optional[str] = None
    chunk_index: Optional[int] = None
    source_info: Optional[str] = None
    source_type: Optional[str] = None
    knowledge_base_id: Optional[str] = None
    uploader_id: Optional[str] = None


# =========================================================
# Query Understanding 相关
# =========================================================

@dataclass
class IntentInfo:
    """
    查询意图信息
    """
    intent: str                        # 意图名称（fact_qa / summarize / compare 等）
    confidence: float                  # 置信度
    signals: Dict[str, float] = field(default_factory=dict)
    language: str = "unknown"


@dataclass
class RewriteInfo:
    """
    查询重写信息
    """
    original: str                      # 原始问题
    rewritten: str                     # 重写后的问题
    expansions: List[str] = field(default_factory=list)
    applied_rules: List[str] = field(default_factory=list)


# =========================================================
# Prompt / 推理过程
# =========================================================

@dataclass
class PromptPayload:
    """
    发送给 LLM 的 Prompt 数据
    """
    system_prompt: str
    user_prompt: str


@dataclass
class RAGDebugInfo:
    """
    RAG 推理过程调试信息（用于日志 / 调试 / 评估）
    """
    intent: Optional[IntentInfo] = None
    rewrite: Optional[RewriteInfo] = None
    retrieved_chunks: List[RetrievalChunk] = field(default_factory=list)
    hit_count: int = 0
    knowledge_base_id: Optional[str] = None


# =========================================================
# ask 接口输入 / 输出
# =========================================================

@dataclass
class AskRequest:
    """
    ask 接口请求结构（逻辑层，不绑定 HTTP）
    """
    question: str
    knowledge_base_id: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    stream: bool = False


@dataclass
class AskResponse:
    """
    ask 接口返回结构（非流式）
    """
    answer: str
    citations: List[Citation] = field(default_factory=list)
    debug: Optional[RAGDebugInfo] = None


@dataclass
class AskStreamResponse:
    """
    ask 接口返回结构（流式）

    - stream: 可迭代对象，yield 字符串
    """
    stream: Any
    citations: List[Citation] = field(default_factory=list)
    debug: Optional[RAGDebugInfo] = None


# =========================================================
# 评估 / 质量相关（预留）
# =========================================================

@dataclass
class AnswerQuality:
    """
    回答质量评估结果（可选模块）
    """
    grounded_score: Optional[float] = None      # 是否基于资料（0~1）
    citation_coverage: Optional[float] = None   # 引用覆盖率
    completeness: Optional[float] = None        # 回答完整性
    comments: Optional[str] = None
