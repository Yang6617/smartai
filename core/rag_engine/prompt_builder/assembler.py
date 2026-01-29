from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .templates import PromptTemplate
from .safety import SafetyGuard
from core.rag_engine.retrieval.vector_retriever import RetrievalHit


@dataclass
class AssembledPrompt:
    """
    组装完成的 Prompt
    """
    system_prompt: str
    user_prompt: str
    citations: List[dict]   # 引用信息（给后处理用）


class PromptAssembler:
    """
    Prompt 组装器

    将 RetrievalHit 列表转为带编号的上下文文本
    """

    def assemble(
        self,
        template: PromptTemplate,
        question: str,
        hits: List[RetrievalHit],
    ) -> AssembledPrompt:
        """
        组装 Prompt
        """
        context_blocks = []
        citations = []

        for idx, hit in enumerate(hits, start=1):
            block = f"[{idx}] {hit.text}"
            context_blocks.append(block)

            citations.append({
                "index": idx,
                "document_id": hit.document_id,
                "chunk_index": hit.chunk_index,
                "source_info": hit.source_info,
                "knowledge_base_id": hit.knowledge_base_id,
            })

        context_text = "\n\n".join(context_blocks)

        # 安全约束
        safety_notice = SafetyGuard.ensure_context_or_refuse(context_text)
        citation_notice = SafetyGuard.enforce_citation_instruction()

        system_prompt = "\n".join(
            p for p in [template.system_prompt, safety_notice, citation_notice] if p
        )

        user_prompt = template.user_prompt.format(
            question=question,
            context=context_text,
        )

        return AssembledPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            citations=citations,
        )
