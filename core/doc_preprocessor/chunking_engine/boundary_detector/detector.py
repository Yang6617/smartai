"""
语义边界检测器
检测文本中的自然转换点，根据内容类型识别边界
"""
import re
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

class BoundaryType(Enum):
    """边界类型枚举"""
    HEADING = "heading"  # 标题边界
    LIST_ITEM = "list_item"  # 列表项边界
    CODE_BLOCK = "code_block"  # 代码块边界
    TABLE = "table"  # 表格边界
    PARAGRAPH = "paragraph"  # 段落边界
    SECTION = "section"  # 章节边界
    CUSTOM = "custom"  # 自定义边界


class Boundary:
    """边界对象"""
    def __init__(self, position: int, boundary_type: BoundaryType, metadata: Dict[str, Any] = None):
        self.position = position
        self.type = boundary_type
        self.metadata = metadata or {}


class BoundaryDetector(ABC):
    """语义边界检测器抽象基类"""
    
    @abstractmethod
    def detect_boundaries(self, text: str, element_type: str = "paragraph") -> List[Boundary]:
        """
        检测文本中的边界
        
        Args:
            text: 待检测的文本
            element_type: 元素类型
            
        Returns:
            边界列表
        """
        pass


class MarkdownBoundaryDetector(BoundaryDetector):
    """Markdown语义边界检测器"""
    
    def detect_boundaries(self, text: str, element_type: str = "paragraph") -> List[Boundary]:
        """
        检测Markdown文本中的边界
        
        Args:
            text: Markdown文本
            element_type: 元素类型（这里主要是"markdown"）
            
        Returns:
            边界列表
        """
        boundaries = []
        
        # 检测标题边界
        heading_pattern = re.compile(r'^(\#{1,6})\s+(.+)$', re.MULTILINE)
        for match in heading_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.start(),
                boundary_type=BoundaryType.HEADING,
                metadata={
                    "level": len(match.group(1)),
                    "title": match.group(2),
                    "marker": match.group(1)
                }
            ))
        
        # 检测代码块边界
        code_fence_pattern = re.compile(r'^(`{3,}|~{3,})', re.MULTILINE)
        for match in code_fence_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.start(),
                boundary_type=BoundaryType.CODE_BLOCK,
                metadata={
                    "fence": match.group(1),
                    "start": True
                }
            ))
        
        # 检测列表项边界
        list_item_pattern = re.compile(r'^(\s*)([*+-]|\d+\.)\s+', re.MULTILINE)
        for match in list_item_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.start(),
                boundary_type=BoundaryType.LIST_ITEM,
                metadata={
                    "indentation": len(match.group(1)),
                    "marker": match.group(2)
                }
            ))
        
        # 检测表格边界（以|开头的行）
        table_pattern = re.compile(r'^\s*\|.*\|\s*$', re.MULTILINE)
        for match in table_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.start(),
                boundary_type=BoundaryType.TABLE,
                metadata={}
            ))
        
        boundaries.sort(key=lambda x: x.position)
        return boundaries


class GenericTextBoundaryDetector(BoundaryDetector):
    """通用文本语义边界检测器"""
    
    def detect_boundaries(self, text: str, element_type: str = "paragraph") -> List[Boundary]:
        """
        检测通用文本中的边界
        
        Args:
            text: 通用文本
            element_type: 元素类型
            
        Returns:
            边界列表
        """
        boundaries = []
        
        # 检测段落边界（两个换行符）
        paragraph_pattern = re.compile(r'\n\s*\n')
        for match in paragraph_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.end(),
                boundary_type=BoundaryType.PARAGRAPH,
                metadata={
                    "separator": match.group()
                }
            ))
        
        # 检测项目符号边界
        bullet_pattern = re.compile(r'^(\s*)([*+-]|\d+\.)\s+', re.MULTILINE)
        for match in bullet_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.start(),
                boundary_type=BoundaryType.LIST_ITEM,
                metadata={
                    "indentation": len(match.group(1)),
                    "marker": match.group(2)
                }
            ))
        
        # 检测缩进边界
        indent_pattern = re.compile(r'^( {2,}|\t+)', re.MULTILINE)
        for match in indent_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.start(),
                boundary_type=BoundaryType.SECTION,
                metadata={
                    "indentation": match.group(1)
                }
            ))
        
        # 检测换行符边界
        newline_pattern = re.compile(r'\n')
        for match in newline_pattern.finditer(text):
            boundaries.append(Boundary(
                position=match.end(),
                boundary_type=BoundaryType.CUSTOM,
                metadata={
                    "type": "newline"
                }
            ))
        
        boundaries.sort(key=lambda x: x.position)
        return boundaries


class BoundaryDetectorFactory:
    """边界检测器工厂类"""
    
    @staticmethod
    def get_detector(file_type: str) -> BoundaryDetector:
        """
        根据文件类型获取相应的边界检测器
        
        Args:
            file_type: 文件类型
            
        Returns:
            对应的边界检测器实例
        """
        if file_type.lower() in ['markdown', 'md']:
            return MarkdownBoundaryDetector()
        else:
            return GenericTextBoundaryDetector()