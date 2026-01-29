"""
OCR专用清洗器模块
包含OCR格式专用的文本清洗功能
"""

# 导入主要的清洗器类
from .interfaces import OCRTextCleaner
from .specific_cleaner import OCRSpecificCleaner
from .config import OCRCleanerConfig

# 定义模块公开的接口
__all__ = [
    'OCRTextCleaner',
    'OCRSpecificCleaner',
    'OCRCleanerConfig'
]