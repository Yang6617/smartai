"""
文档预处理器配置
定义文档解析模块的配置参数
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DocPreprocessorConfig:
    """文档预处理器配置"""
    
    # 默认配置值
    chunk_size: int = 512  # 文本块大小
    chunk_overlap: int = 50  # 文本块重叠大小
    max_file_size: int = 10 * 1024 * 1024  # 最大文件大小（字节），默认10MB
    supported_formats: list = None  # 支持的文件格式列表
    
    def __post_init__(self):
        """初始化后处理"""
        if self.supported_formats is None:
            self.supported_formats = ['.txt', '.md', '.pdf', '.docx', '.html']