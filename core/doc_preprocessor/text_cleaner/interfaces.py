"""
文本清洗器接口定义

定义文本清洗器的通用接口，所有具体的清洗器都需要实现此接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path

# 导入Element类以便使用
try:
    from ..parsing_cluster.processor import Element
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from core.doc_preprocessor.parsing_cluster.processor import Element


class TextCleaner(ABC):
    """
    文本清洗器抽象基类
    所有文本清洗器都应该继承此类并实现clean方法
    """
    
    @abstractmethod
    def clean(self, elements: List[Element]) -> List[Element]:
        """
        清洗Element列表中的文本内容
        
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


class CleanerConfig:
    """
    清洗器配置类
    定义清洗器的通用配置选项
    """
    
    def __init__(self):
        # 空白字符标准化配置
        self.normalize_whitespace = True  # 是否标准化空白字符
        self.remove_leading_trailing = True  # 是否去除首尾空白
        self.convert_full_width_spaces = True  # 是否转换全角空格
        
        # 编码规范化配置
        self.normalize_full_width_chars = True  # 是否转换全角字符
        self.fix_common_mojibake = True  # 是否修复常见乱码
        self.unify_punctuation = True  # 是否统一标点符号
        
        # 换行符统一配置
        self.normalize_line_breaks = True  # 是否统一换行符
        self.max_consecutive_newlines = 2  # 最大连续换行符数量