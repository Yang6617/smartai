"""
文档预处理器模块
提供文档解析的基础框架
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import uuid
from pathlib import Path
from datetime import datetime


class Element:
    """Element对象 - 解析集群的基本输出单位"""
    
    def __init__(self, 
                 raw_content: str,
                 element_type: str,
                 element_index: int,
                 source_format: str,
                 format_metadata: Optional[Dict[str, Any]] = None,
                 parser_confidence: float = 1.0):
        """
        初始化Element对象
        
        Args:
            raw_content: 从源文件中提取的原始文本内容
            element_type: 元素的逻辑类型标识
            element_index: 元素在原始文档解析流中的全局顺序索引
            source_format: 源文件的格式类型
            format_metadata: 解析过程中产生的专有信息字典
            parser_confidence: 解析器对此元素提取准确性的置信度
        """
        self.raw_content = raw_content
        self.element_type = element_type
        self.element_index = element_index
        self.source_format = source_format
        self.element_id = f"elem_{str(uuid.uuid4())[:8]}_{element_index}"  # 总是生成ID
        self.format_metadata = format_metadata or {}
        self.parser_confidence = parser_confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "element_id": self.element_id,
            "raw_content": self.raw_content,
            "element_type": self.element_type,
            "element_index": self.element_index,
            "source_format": self.source_format,
            "format_metadata": self.format_metadata,
            "parser_confidence": self.parser_confidence
        }


class DocumentParser(ABC):
    """文档解析器抽象基类"""
    
    @abstractmethod
    def parse(self, file_path: str, user_id: str, knowledge_base_id: str) -> Dict[str, Any]:
        """
        解析文档
        
        Args:
            file_path: 文件路径（来自用户上传）
            user_id: 用户ID
            knowledge_base_id: 知识库ID（团队ID）
            
        Returns:
            解析后的JSON格式数据，格式为：
            {
                "user_id": str,
                "file_name": str,
                "knowledge_base_id": str,
                "elements": List[Element]
            }
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            支持的文件扩展名列表
        """
        pass


class ParseResult:
    """解析结果数据结构 - 符合新规范的输出格式"""
    
    def __init__(self, 
                 user_id: str,
                 file_name: str,
                 knowledge_base_id: str,
                 elements: List[Element]):
        """
        初始化解析结果
        
        Args:
            user_id: 用户ID
            file_name: 文件名
            knowledge_base_id: 知识库ID（团队ID）
            elements: Element对象列表
        """
        self.user_id = user_id
        self.file_name = file_name
        self.knowledge_base_id = knowledge_base_id
        self.elements = elements
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "file_name": self.file_name,
            "knowledge_base_id": self.knowledge_base_id,
            "elements": [elem.to_dict() for elem in self.elements]
        }


class DocumentProcessor:
    """文档处理器 - 负责协调不同类型的解析器"""
    
    def __init__(self):
        """初始化文档处理器"""
        self.parsers: Dict[str, DocumentParser] = {}
    
    def register_parser(self, parser: DocumentParser):
        """
        注册解析器
        
        Args:
            parser: 文档解析器实例
        """
        for file_ext in parser.get_supported_formats():
            self.parsers[file_ext.lower()] = parser
            print(f"注册解析器: {file_ext} -> {parser.__class__.__name__}")
    
    def get_parser_for_file(self, file_path: str) -> Optional[DocumentParser]:
        """
        根据文件路径获取对应的解析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            对应的解析器，如果未找到则返回None
        """
        file_ext = Path(file_path).suffix.lower()
        return self.parsers.get(file_ext)
    
    def process_document(self, file_path: str, user_id: str, knowledge_base_id: str) -> Dict[str, Any]:
        """
        处理文档
        
        Args:
            file_path: 文件路径（来自用户上传）
            user_id: 上传用户ID
            knowledge_base_id: 知识库ID（团队ID）
            
        Returns:
            解析后的JSON格式数据，格式为：
            {
                "user_id": str,
                "file_name": str,
                "knowledge_base_id": str,
                "elements": List[Element]
            }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        parser = self.get_parser_for_file(file_path)
        if parser is None:
            raise ValueError(f"不支持的文件格式: {Path(file_path).suffix}")
        
        # 使用对应的解析器解析文件
        result = parser.parse(file_path, user_id, knowledge_base_id)
        return result
    
    def get_supported_formats(self) -> List[str]:
        """
        获取所有支持的文件格式
        
        Returns:
            支持的文件格式列表
        """
        formats = set()
        for parser in self.parsers.values():
            formats.update(parser.get_supported_formats())
        return sorted(list(formats))