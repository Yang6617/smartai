"""
Chunk对象定义和JSON输出格式
定义分块结果的数据结构
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ChunkType(Enum):
    """分块类型枚举"""
    TEXT = "text"
    CODE = "code"
    TABLE = "table"
    LIST = "list"
    HEADING = "heading"


@dataclass
class Chunk:
    """
    分块对象
    对应参考JSON结构中的chunks数组中的元素
    """
    text: str  # 分块的文本内容，对应JSON中的"text"
    chunk_index: int  # 分块索引，对应JSON中的"chunk_index"
    structure_path: Optional[List[str]] = None  # 结构路径，对应JSON中的"structure_path"
    element_type: Optional[str] = None  # 元素类型
    chunk_type: Optional[ChunkType] = None  # 分块类型
    metadata: Optional[Dict[str, Any]] = None  # 元数据
    format_metadata: Optional[Dict[str, Any]] = None  # 格式特定元数据（用于存储bbox等信息）
    overlap_info: Optional[Dict[str, Any]] = None  # 重叠信息
    confidence: Optional[float] = None  # 置信度
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化"""
        result = {
            "text": self.text,
            "chunk_index": self.chunk_index,
        }
        
        # 只有当字段有值时才添加到结果中
        if self.structure_path is not None:
            result["structure_path"] = self.structure_path
        if self.element_type is not None:
            result["element_type"] = self.element_type
        if self.chunk_type is not None:
            result["chunk_type"] = self.chunk_type.value
        if self.metadata is not None:
            result["metadata"] = self.metadata
        if self.format_metadata is not None:
            result["format_metadata"] = self.format_metadata
        if self.overlap_info is not None:
            result["overlap_info"] = self.overlap_info
        if self.confidence is not None:
            result["confidence"] = self.confidence
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chunk':
        """从字典创建Chunk对象"""
        chunk_type = None
        if 'chunk_type' in data and data['chunk_type'] is not None:
            try:
                chunk_type = ChunkType(data['chunk_type'])
            except ValueError:
                chunk_type = ChunkType.TEXT  # 默认类型
        
        return cls(
            text=data.get('text', ''),
            chunk_index=data.get('chunk_index', 0),
            structure_path=data.get('structure_path'),
            element_type=data.get('element_type'),
            chunk_type=chunk_type,
            metadata=data.get('metadata'),
            format_metadata=data.get('format_metadata'),
            overlap_info=data.get('overlap_info'),
            confidence=data.get('confidence')
        )


def format_chunks_for_output(chunks: List[Chunk], document_id: str, team_id: str, user_id: str, file_name: str, file_type: str) -> Dict[str, Any]:
    """
    将分块结果格式化为指定的JSON输出格式
    
    Args:
        chunks: 分块对象列表
        document_id: 文档ID
        team_id: 团队ID
        user_id: 用户ID
        file_name: 文件名
        file_type: 文件类型
        
    Returns:
        符合参考格式的字典
    """
    return {
        "document_id": document_id,
        "team_id": team_id,
        "user_id": user_id,
        "file_name": file_name,
        "file_type": file_type,
        "chunks": [chunk.to_dict() for chunk in chunks]
    }