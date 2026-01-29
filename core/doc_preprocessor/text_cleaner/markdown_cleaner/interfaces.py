"""
Markdown专用清洗器接口定义

定义Markdown格式专用的清洗器接口，用于处理Markdown文档特有的格式问题
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.doc_preprocessor.parsing_cluster.processor import Element


class MarkdownTextCleaner(ABC):
    """
    Markdown专用清洗器抽象基类
    继承自TextCleaner，专门处理Markdown格式的文本内容
    """
    
    @abstractmethod
    def clean(self, elements: List[Element]) -> List[Element]:
        """
        清洗Element列表中的Markdown文本内容
        
        Args:
            elements: 待清洗的Element对象列表
            
        Returns:
            清洗后的Element对象列表
        """
        pass
        
    @abstractmethod
    def get_cleaner_info(self) -> Dict[str, Any]:
        """
        获取清洗器的基本信息
        
        Returns:
            包含清洗器名称、描述等信息的字典
        """
        pass