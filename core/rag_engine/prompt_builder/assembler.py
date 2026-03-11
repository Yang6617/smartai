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
        doc_chunks_map = {}  # 记录每个文档包含的chunks

        for idx, hit in enumerate(hits, start=1):
            # 如果有source_info（标题层级），添加到上下文中
            if hit.source_info:
                block = f"[{idx}] (来源: {hit.source_info})\n{hit.text}"
            else:
                block = f"[{idx}] {hit.text}"
            context_blocks.append(block)

            citations.append({
                "index": idx,
                "document_id": hit.document_id,
                "chunk_index": hit.chunk_index,
                "source_info": hit.source_info,
                "knowledge_base_id": hit.knowledge_base_id,
            })
            
            # 记录每个文档包含的chunks
            if hit.document_id:
                if hit.document_id not in doc_chunks_map:
                    doc_chunks_map[hit.document_id] = {
                        "chunks": [],
                        "source_info": hit.source_info or "未知来源"
                    }
                doc_chunks_map[hit.document_id]["chunks"].append({
                    "index": idx,
                    "chunk_index": hit.chunk_index,
                    "source_info": hit.source_info
                })

        context_text = "\n\n".join(context_blocks)
        
        # 构建文档来源说明
        doc_source_notice = self._build_document_source_notice(doc_chunks_map)

        # 安全约束
        safety_notice = SafetyGuard.ensure_context_or_refuse(context_text)
        citation_notice = SafetyGuard.enforce_citation_instruction()

        system_prompt = "\n".join(
            p for p in [template.system_prompt, safety_notice, citation_notice] if p
        )
        
        # 如果有文档来源说明，添加到system_prompt中
        if doc_source_notice:
            system_prompt = f"{system_prompt}\n\n{doc_source_notice}"

        user_prompt = template.user_prompt.format(
            question=question,
            context=context_text,
        )

        return AssembledPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            citations=citations,
        )
    
    def _build_document_source_notice(self, doc_chunks_map: dict) -> str:
        """
        构建文档来源说明
        
        Args:
            doc_chunks_map: 文档到chunks的映射
            
        Returns:
            文档来源说明文本
        """
        if not doc_chunks_map:
            return ""
        
        notice_lines = ["【参考资料说明】"]
        notice_lines.append("以下参考资料中，相同文档ID的多个条目来自同一个文档的不同部分。")
        notice_lines.append("请根据内容相关性选择合适的引用编号。")
        notice_lines.append("")
        
        for doc_id, info in doc_chunks_map.items():
            chunks_info = info["chunks"]
            if len(chunks_info) > 1:
                chunk_indices = [str(c["index"]) for c in chunks_info]
                source_info = info["source_info"]
                notice_lines.append(f"- 文档（来源: {source_info}）包含分块: [{', '.join(chunk_indices)}]")
        
        return "\n".join(notice_lines)
