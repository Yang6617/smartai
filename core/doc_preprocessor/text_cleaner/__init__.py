"""
文本清洗器模块
包含各种文本清洗功能
"""

# 导入主要的清洗器类
from .basic_cleaner import BasicTextCleaner
from .config import TextCleanerConfig, get_default_config, get_aggressive_config, get_light_config

# 导入Markdown专用清洗器
from .markdown_cleaner import MarkdownSpecificCleaner, MarkdownCleanerConfig

# 导入OCR专用清洗器
from .ocr_cleaner import OCRSpecificCleaner, OCRCleanerConfig

# 定义模块公开的接口
__all__ = [
    'BasicTextCleaner',
    'TextCleanerConfig',
    'get_default_config',
    'get_aggressive_config',
    'get_light_config',
    'MarkdownSpecificCleaner',
    'MarkdownCleanerConfig',
    'OCRSpecificCleaner',
    'OCRCleanerConfig'
]