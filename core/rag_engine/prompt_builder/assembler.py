from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.rag_engine.prompt_builder.templates import PromptTemplate
from core.rag_engine.prompt_builder.safety import SafetyGuard
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

    def __init__(
            self,
            max_context_chunks: int = 8,
            max_context_chars: int = 5000,
    ) -> None:
        self.max_context_chunks = max_context_chunks
        self.max_context_chars = max_context_chars
    def assemble(
        self,
        template: PromptTemplate,
        question: str,
        hits: List[RetrievalHit],
    ) -> AssembledPrompt:
        # 1) 去重
        dedup_hits = self._dedupe_hits(hits)

        # 2) 截断 chunk 数
        dedup_hits = dedup_hits[: self.max_context_chunks]

        # 3) 构造上下文块 + citations
        context_blocks = []
        citations = []
        total_chars = 0

        for idx, hit in enumerate(dedup_hits, start=1):
            block = self._format_context_block(idx, hit)
            block_len = len(block)

            if total_chars + block_len > self.max_context_chars:
                break

            context_blocks.append(block)
            total_chars += block_len

            citations.append({
                "index": idx,
                "document_id": hit.document_id,
                "chunk_index": hit.chunk_index,
                "source_info": hit.source_info,
                "knowledge_base_id": hit.knowledge_base_id,
                "retriever": hit.retriever,
            })

        context_text = "\n\n".join(context_blocks)

        # 4) 安全约束
        safety_notice = SafetyGuard.ensure_context_or_refuse(context_text)
        citation_notice = SafetyGuard.enforce_citation_instruction()
        answer_notice = SafetyGuard.enforce_answer_style()

        system_prompt = "\n".join(
            p for p in [
                template.system_prompt,
                safety_notice,
                citation_notice,
                answer_notice,
            ] if p
        )

        user_prompt = template.user_prompt.format(
            question=question,
            context=context_text if context_text.strip() else "（无可用参考资料）",
        )

        return AssembledPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            citations=citations,
        )

    def _format_context_block(self, idx: int, hit: RetrievalHit) -> str:
        doc_id = hit.document_id or "unknown"
        chunk_idx = hit.chunk_index if hit.chunk_index is not None else "unknown"
        retriever = hit.retriever or "unknown"
        text = (hit.text or "").strip()

        return (
            f"[{idx}]\n"
            f"来源文档: {doc_id}\n"
            f"分块序号: {chunk_idx}\n"
            f"检索方式: {retriever}\n"
            f"内容:\n{text}"
        )

    def _dedupe_hits(self, hits: List[RetrievalHit]) -> List[RetrievalHit]:
        seen = set()
        results = []

        for hit in hits:
            if hit.document_id is not None and hit.chunk_index is not None:
                key = f"{hit.document_id}::chunk::{hit.chunk_index}"
            else:
                key = f"id::{hit.id}"

            if key in seen:
                continue

            seen.add(key)
            results.append(hit)

        return results
