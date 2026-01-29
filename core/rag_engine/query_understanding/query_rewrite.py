from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class RewriteResult:
    """
    查询重写结果
    """
    original: str                        # 原始查询
    rewritten: str                       # 重写后的查询
    expansions: List[str] = field(default_factory=list)   # 扩展查询（用于提升召回）
    applied_rules: List[str] = field(default_factory=list)  # 应用的规则
    warnings: List[str] = field(default_factory=list)       # 风险提示


class QueryRewriter:
    """
    查询重写与规范化模块

    目标：
    - 统一格式
    - 去噪（礼貌词、冗余词）
    - 轻量同义词扩展
    - 拼接上下文/知识库提示
    """

    def __init__(self, enable_expansion: bool = True) -> None:
        self.enable_expansion = enable_expansion

        # 轻量同义词扩展表
        self._synonyms: List[Tuple[str, List[str]]] = [
            ("RAG", ["检索增强生成", "Retrieval Augmented Generation"]),
            ("向量库", ["vector database", "vectordb"]),
            ("ChromaDB", ["chroma", "chromadb"]),
            ("embedding", ["向量", "嵌入"]),
        ]

        # 常见口语/礼貌填充词
        self._fillers = ["请问", "麻烦", "帮我", "一下", "可以", "请", "谢谢"]

    def rewrite(self, query: str, hints: Optional[Dict[str, str]] = None) -> RewriteResult:
        """
        对查询进行重写
        """
        original = (query or "").strip()
        q = original
        applied, warnings = [], []

        if not q:
            return RewriteResult(original=original, rewritten="", warnings=["空查询"])

        # 空白规范化
        q2 = " ".join(q.split())
        if q2 != q:
            applied.append("normalize_whitespace")
            q = q2

        # 中文标点规范化
        q2 = q.replace("，", ",").replace("。", ".").replace("？", "?")
        if q2 != q:
            applied.append("normalize_punctuation")
            q = q2

        # 去除口语填充词
        q2 = q
        for f in self._fillers:
            q2 = q2.replace(f, "")
        q2 = " ".join(q2.split()).strip()
        if q2 != q:
            applied.append("remove_fillers")
            q = q2

        # 拼接上下文提示（如 knowledge_base_id）
        if hints:
            tokens = []
            if hints.get("knowledge_base_id"):
                tokens.append(f"kb:{hints['knowledge_base_id']}")
            if hints.get("file_type"):
                tokens.append(f"type:{hints['file_type']}")
            if tokens:
                q = f"{q} ({' '.join(tokens)})"
                applied.append("append_hints")

        expansions = []
        if self.enable_expansion:
            expansions = self._expand_synonyms(original)
            if expansions:
                applied.append("synonym_expansion")

        if len(q) < 2:
            warnings.append("重写后查询过短")

        return RewriteResult(
            original=original,
            rewritten=q,
            expansions=expansions,
            applied_rules=applied,
            warnings=warnings,
        )

    def _expand_synonyms(self, query: str) -> List[str]:
        """
        基于同义词表生成扩展查询
        """
        results = []
        lower = query.lower()
        for key, syns in self._synonyms:
            if key.lower() in lower:
                results.extend(query.replace(key, s) for s in syns)
            else:
                for s in syns:
                    if s.lower() in lower:
                        results.append(query.replace(s, key))
        return list(dict.fromkeys(results))[:5]
