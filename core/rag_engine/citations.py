from __future__ import annotations

import re
from typing import Dict, List, Optional

from core.rag_engine.types import Citation
from core.rag_engine.retrieval.vector_retriever import RetrievalHit


class CitationManager:
    """
    引用管理器

    职责：
    - 生成 Citation 列表
    - 校验回答是否引用了资料
    - 提取回答中使用的引用编号
    """

    CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    @staticmethod
    def build_citations(hits: List[RetrievalHit]) -> List[Citation]:
        """
        根据检索结果构建 Citation 列表
        """
        citations: List[Citation] = []
        for idx, hit in enumerate(hits, start=1):
            citations.append(
                Citation(
                    index=idx,
                    document_id=hit.document_id,
                    chunk_index=hit.chunk_index,
                    source_info=hit.source_info,
                    knowledge_base_id=hit.knowledge_base_id,
                )
            )
        return citations

    @classmethod
    def extract_used_citation_indexes(cls, answer_text: str) -> List[int]:
        """
        从回答文本中提取被使用的引用编号
        """
        if not answer_text:
            return []
        return sorted(
            {int(m.group(1)) for m in cls.CITATION_PATTERN.finditer(answer_text)}
        )

    @classmethod
    def validate_citations(
        cls,
        answer_text: str,
        citations: List[Citation],
        require_citation: bool = True,
    ) -> Dict[str, any]:
        """
        校验回答的引用情况

        返回：
        - valid: 是否通过校验
        - used_indexes: 实际使用的引用编号
        - unused_indexes: 未使用的引用编号
        - issues: 问题描述
        """
        used = cls.extract_used_citation_indexes(answer_text)
        all_indexes = {c.index for c in citations}

        unused = sorted(all_indexes - set(used))
        issues = []

        if require_citation and not used:
            issues.append("回答中未发现任何引用标记")

        if used:
            invalid = [i for i in used if i not in all_indexes]
            if invalid:
                issues.append(f"回答中使用了不存在的引用编号: {invalid}")

        return {
            "valid": len(issues) == 0,
            "used_indexes": used,
            "unused_indexes": unused,
            "issues": issues,
        }
