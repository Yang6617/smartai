from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from rank_bm25 import BM25Okapi
from core.rag_engine.retrieval.vector_retriever import RetrievalHit
import re
import jieba

@dataclass
class KeywordRetrieverConfig:
    top_k: int = 8

def _contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))

def tokenize_text(text: str) -> List[str]:
    """
    统一分词函数：
    - 中文：jieba 分词
    - 英文/混合：正则切词
    - 最后做归一化清洗
    """
    text = (text or "").strip().lower()
    if not text:
        return []

    tokens: List[str] = []

    # 1) 中文分词
    if _contains_chinese(text):
        for tok in jieba.lcut(text):
            tok = tok.strip().lower()
            if tok:
                tokens.append(tok)

    # 2) 英文 / 数字 / 混合串补充分词
    # 例如：
    # rag_engine -> rag_engine
    # v1.2.0 -> v1.2.0
    # api-test -> api-test
    # kb_target -> kb_target
    regex_tokens = re.findall(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", text.lower())
    tokens.extend(regex_tokens)

    # 3) 清洗噪声 token
    cleaned = []
    seen = set()
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue

        # 去掉纯符号
        if re.fullmatch(r"[_\-.]+", tok):
            continue

        # 去掉过短英文噪声（但保留纯中文 token）
        if not _contains_chinese(tok) and len(tok) == 1 and not tok.isdigit():
            continue

        if tok not in seen:
            seen.add(tok)
            cleaned.append(tok)

    return cleaned


class KeywordRetriever:
    """
    关键词检索器（BM25）

    documents 期望格式：
    [
        {
            "id": "...",
            "text": "...",
            "metadata": {...}
        },
        ...
    ]
"""


    def __init__(
        self,
        documents: List[Dict[str, Any]],
        config: Optional[KeywordRetrieverConfig] = None
    ):
        self.config = config or KeywordRetrieverConfig()
        self.documents = documents or []

        self.tokenized_corpus: List[List[str]] = []
        valid_documents: List[Dict[str, Any]] = []

        for doc in self.documents:
            text = str(doc.get("text", "")).strip()
            if not text:
                continue

            tokens = tokenize_text(text)
            if not tokens:
                continue

            valid_documents.append(doc)
            self.tokenized_corpus.append(tokens)

        self.documents = valid_documents
        self.bm25 = BM25Okapi(self.tokenized_corpus) if self.tokenized_corpus else None

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievalHit]:
        k = int(top_k or self.config.top_k)

        if not self.bm25:
            return []

        q_terms = tokenize_text(query)
        if not q_terms:
            return []

        scores = self.bm25.get_scores(q_terms)
        ranked_idx = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )

        hits: List[RetrievalHit] = []
        for idx in ranked_idx[:k]:
            score = float(scores[idx])
            if score <= 0:
                continue

            doc = self.documents[idx]
            metadata = doc.get("metadata", {}) or {}
            if not isinstance(metadata, dict):
                metadata = {}

            hit = RetrievalHit(
                id=str(doc.get("id", idx)),
                score=score,
                text=str(doc.get("text", "")),
                metadata=metadata,
                document_id=metadata.get("document_id"),
                chunk_index=metadata.get("chunk_index"),
                source_info=metadata.get("source_info"),
                source_type=metadata.get("source_type"),
                knowledge_base_id=metadata.get("knowledge_base_id"),
                uploader_id=metadata.get("uploader_id"),
                retriever="keyword",
            )
            hits.append(hit)

        return hits
