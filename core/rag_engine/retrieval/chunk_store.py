from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
from pathlib import Path


@dataclass
class ChunkRecord:
    id: str
    text: str
    metadata: Dict[str, Any]


class ChunkStore:
    """
    轻量 chunk 存储：
    - 每个知识库一份 json 文件
    - 用于 BM25 建索引
    - 用于按 document_id / chunk_index 做邻接扩展
    """

    def __init__(self, base_dir: str = "./data/chunk_store") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _kb_path(self, kb_id: str) -> Path:
        return self.base_dir / f"{kb_id}.json"

    def save_kb_documents(self, kb_id: str, documents: List[Dict[str, Any]]) -> None:
        path = self._kb_path(kb_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

    def load_kb_documents(self, kb_id: str) -> List[Dict[str, Any]]:
        path = self._kb_path(kb_id)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def append_documents(self, kb_id: str, documents: List[Dict[str, Any]]) -> None:
        old_docs = self.load_kb_documents(kb_id)
        old_ids = {str(d.get("id")) for d in old_docs}

        for doc in documents:
            doc_id = str(doc.get("id"))
            if doc_id not in old_ids:
                old_docs.append(doc)

        self.save_kb_documents(kb_id, old_docs)

    def get_neighbors(
        self,
        kb_id: str,
        document_id: str,
        chunk_index: int,
        window: int = 1,
    ) -> List[Dict[str, Any]]:
        docs = self.load_kb_documents(kb_id)
        result = []

        for doc in docs:
            md = doc.get("metadata", {}) or {}
            if md.get("document_id") != document_id:
                continue

            idx = md.get("chunk_index")
            try:
                idx = int(idx)
            except Exception:
                continue

            if chunk_index - window <= idx <= chunk_index + window:
                result.append(doc)

        result.sort(key=lambda d: int((d.get("metadata", {}) or {}).get("chunk_index", 0)))
        return result