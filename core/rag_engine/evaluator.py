from __future__ import annotations

from typing import List, Optional

from core.rag_engine.types import (
    AnswerQuality,
    Citation,
    RetrievalChunk,
)
from core.rag_engine.citations import CitationManager


class RAGEvaluator:
    """
    RAG 回答质量评估器

    评估维度：
    - 是否基于检索资料（grounded）
    - 引用覆盖率
    - 回答完整性（粗略启发式）
    """

    def evaluate(
        self,
        answer_text: str,
        citations: List[Citation],
        retrieved_chunks: Optional[List[RetrievalChunk]] = None,
    ) -> AnswerQuality:
        """
        对一次 RAG 回答进行质量评估
        """
        quality = AnswerQuality()

        if not answer_text:
            quality.grounded_score = 0.0
            quality.comments = "回答为空"
            return quality

        # ===============================
        # 1. 基于引用的 grounded 评估
        # ===============================
        citation_check = CitationManager.validate_citations(
            answer_text=answer_text,
            citations=citations,
            require_citation=True,
        )

        if citation_check["used_indexes"]:
            quality.grounded_score = 1.0
        else:
            quality.grounded_score = 0.3

        # ===============================
        # 2. 引用覆盖率
        # ===============================
        total = len(citations)
        used = len(citation_check["used_indexes"])
        quality.citation_coverage = used / total if total > 0 else 0.0

        # ===============================
        # 3. 回答完整性（非常保守的启发式）
        # ===============================
        # 规则示例：
        # - 太短 → 不完整
        # - 使用多个引用 → 可能更完整
        length_score = min(len(answer_text) / 300, 1.0)
        citation_bonus = min(quality.citation_coverage * 0.5, 0.5)
        quality.completeness = min(length_score + citation_bonus, 1.0)

        # ===============================
        # 4. 评估说明
        # ===============================
        comments = []
        if quality.citation_coverage < 0.3:
            comments.append("引用使用较少")
        if quality.completeness < 0.4:
            comments.append("回答可能不够完整")

        quality.comments = "；".join(comments) if comments else "评估正常"
        return quality
