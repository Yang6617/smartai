from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from core.rag_engine.retrieval.vector_retriever import RetrievalHit
from core.rag_engine.retrieval.chunk_store import ChunkStore


@dataclass
class ChunkExpansionConfig:
    window: int = 1
    max_added_chunks: int = 4


class ChunkExpander:
    def __init__(
        self,
        chunk_store: ChunkStore,
        config: Optional[ChunkExpansionConfig] = None,
    ) -> None:
        self.chunk_store = chunk_store
        self.config = config or ChunkExpansionConfig()

    def expand(
        self,
        kb_id: str,
        hits: List[RetrievalHit],
    ) -> List[RetrievalHit]:
        if not kb_id or not hits:
            return hits

        results: List[RetrievalHit] = []
        seen = set()

        # 先放原始命中
        for hit in hits:
            key = self._dedupe_key(hit.document_id, hit.chunk_index, hit.id)
            if key not in seen:
                seen.add(key)
                results.append(hit)

        added = 0

        for hit in hits:
            if added >= self.config.max_added_chunks:
                break

            if not hit.document_id or hit.chunk_index is None:
                continue

            neighbors = self.chunk_store.get_neighbors(
                kb_id=kb_id,
                document_id=hit.document_id,
                chunk_index=hit.chunk_index,
                window=self.config.window,
            )

            for doc in neighbors:
                md = doc.get("metadata", {}) or {}
                neighbor_chunk_index = md.get("chunk_index")
                key = self._dedupe_key(
                    md.get("document_id"),
                    neighbor_chunk_index,
                    doc.get("id"),
                )
                if key in seen:
                    continue

                seen.add(key)
                added += 1

                results.append(
                    RetrievalHit(
                        id=str(doc.get("id")),
                        score=max(hit.score * 0.85, 1e-6),  # 扩展块分数略低
                        text=str(doc.get("text", "")),
                        metadata=md,
                        document_id=md.get("document_id"),
                        chunk_index=neighbor_chunk_index,
                        source_info=md.get("source_info"),
                        source_type=md.get("source_type"),
                        knowledge_base_id=md.get("knowledge_base_id"),
                        uploader_id=md.get("uploader_id"),
                        retriever="expanded",
                    )
                )

                if added >= self.config.max_added_chunks:
                    break

        return results

    @staticmethod
    def _dedupe_key(document_id, chunk_index, fallback_id) -> str:
        if document_id is not None and chunk_index is not None:
            return f"{document_id}::chunk::{chunk_index}"
        return f"id::{fallback_id}"