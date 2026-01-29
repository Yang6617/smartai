from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RetrievalFilter:
    """
    检索过滤条件（统一封装）

    - where: 过滤 metadata（例如 knowledge_base_id / uploader_id / document_id）
    - where_document: 过滤 document 字段（例如包含某些关键字）
    """
    knowledge_base_id: Optional[str] = None
    uploader_id: Optional[str] = None
    document_id: Optional[str] = None
    source_type: Optional[str] = None

    # 可扩展：时间范围过滤（需要你们 metadata 的 timestamp 格式一致）
    # start_ts: Optional[str] = None
    # end_ts: Optional[str] = None

    # 文档文本过滤（Chroma where_document 支持 $contains 等，具体取决于版本）
    document_contains: Optional[str] = None

    # 额外自定义过滤（直接并入 where）
    extra_where: Dict[str, Any] = field(default_factory=dict)


def build_where_filter(rf: RetrievalFilter) -> Optional[Dict[str, Any]]:
    """
    构建向量库 query 的 where 过滤条件（metadata 过滤）

    注意：这里不使用复杂的 $and/$or 组合，保持最小可用；
    后续如需要复合条件，可以扩展为 {"$and":[...]} 的结构。
    """
    where: Dict[str, Any] = {}

    if rf.knowledge_base_id:
        where["knowledge_base_id"] = rf.knowledge_base_id
    if rf.uploader_id:
        where["uploader_id"] = rf.uploader_id
    if rf.document_id:
        where["document_id"] = rf.document_id
    if rf.source_type:
        where["source_type"] = rf.source_type

    # 合并额外条件（调用方自行保证不冲突）
    if rf.extra_where:
        where.update(rf.extra_where)

    return where or None


def build_where_document_filter(rf: RetrievalFilter) -> Optional[Dict[str, Any]]:
    """
    构建向量库 query 的 where_document 过滤条件（document 字段过滤）

    说明：Chroma 对 where_document 的语法可能随版本变化：
    - 常见写法：{"$contains": "xxx"} 或 {"$contains": {"text": "..."}}
    这里先选用最常见、最朴素的 {"$contains": "..."}。
    """
    if rf.document_contains and rf.document_contains.strip():
        return {"$contains": rf.document_contains.strip()}
    return None
