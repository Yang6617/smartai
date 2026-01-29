"""
解析策略选择模块

根据文件大小和类型选择最优解析策略
"""
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os


class ParseStrategy(Enum):
    """解析策略枚举"""
    QUICK_PARSE = "quick_parse"        # 快速解析，适用于小文件
    BALANCED_PARSE = "balanced_parse"  # 平衡解析，适用于中等文件
    DEEP_PARSE = "deep_parse"          # 深度解析，适用于大文件或复杂格式
    OCR_PARSE = "ocr_parse"            # OCR解析，适用于图片文件
    STREAM_PARSE = "stream_parse"      # 流式解析，适用于超大文件


@dataclass
class ParseConfig:
    """解析配置"""
    strategy: ParseStrategy
    chunk_size: int = 1024 * 1024  # 1MB
    timeout: int = 300  # 5分钟超时
    enable_ocr: bool = False
    ocr_language: str = 'ch'
    max_workers: int = 4
    memory_limit: int = 512 * 1024 * 1024  # 512MB


class StrategySelector:
    """策略选择器"""
    
    # 文件类型到策略的映射
    TYPE_STRATEGY_MAP = {
        'image/': ParseStrategy.OCR_PARSE,  # 图片类型
        'text/markdown': ParseStrategy.BALANCED_PARSE,
        'text/plain': ParseStrategy.QUICK_PARSE,
        'text/html': ParseStrategy.BALANCED_PARSE,
        'text/xml': ParseStrategy.BALANCED_PARSE,
        'application/pdf': ParseStrategy.DEEP_PARSE,
        'application/msword': ParseStrategy.DEEP_PARSE,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ParseStrategy.DEEP_PARSE,
        'application/vnd.ms-excel': ParseStrategy.DEEP_PARSE,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ParseStrategy.DEEP_PARSE,
        'application/vnd.ms-powerpoint': ParseStrategy.DEEP_PARSE,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ParseStrategy.DEEP_PARSE,
    }
    
    # 文件大小阈值（字节）
    SIZE_THRESHOLDS = {
        'small': 100 * 1024,      # 100KB以下
        'medium': 10 * 1024 * 1024,  # 10MB以下
        'large': 100 * 1024 * 1024,  # 100MB以下
        'huge': float('inf')      # 超大文件
    }

    @classmethod
    def select_strategy(cls, file_path: str, mime_type: str) -> ParseConfig:
        """
        根据文件路径和MIME类型选择解析策略
        
        Args:
            file_path: 文件路径
            mime_type: MIME类型
            
        Returns:
            ParseConfig: 解析配置
        """
        file_size = os.path.getsize(file_path)
        
        # 首先根据文件类型确定基本策略
        base_strategy = cls._get_base_strategy(mime_type)
        
        # 然后根据文件大小调整策略
        adjusted_strategy = cls._adjust_strategy_by_size(base_strategy, file_size)
        
        # 根据策略创建配置
        config = cls._create_config(adjusted_strategy, file_size, mime_type)
        
        return config

    @classmethod
    def _get_base_strategy(cls, mime_type: str) -> ParseStrategy:
        """根据MIME类型获取基础策略"""
        # 检查是否有匹配的特定类型
        for type_pattern, strategy in cls.TYPE_STRATEGY_MAP.items():
            if mime_type.startswith(type_pattern):
                return strategy
        
        # 默认使用平衡解析
        return ParseStrategy.BALANCED_PARSE

    @classmethod
    def _adjust_strategy_by_size(cls, base_strategy: ParseStrategy, file_size: int) -> ParseStrategy:
        """根据文件大小调整策略"""
        if file_size <= cls.SIZE_THRESHOLDS['small']:
            # 小文件通常使用快速解析，除非原本就需要深度解析
            if base_strategy in [ParseStrategy.DEEP_PARSE, ParseStrategy.STREAM_PARSE]:
                return base_strategy
            return ParseStrategy.QUICK_PARSE
        elif file_size <= cls.SIZE_THRESHOLDS['medium']:
            # 中等文件使用平衡解析
            if base_strategy in [ParseStrategy.DEEP_PARSE, ParseStrategy.STREAM_PARSE]:
                return base_strategy
            return ParseStrategy.BALANCED_PARSE
        elif file_size <= cls.SIZE_THRESHOLDS['large']:
            # 大文件使用深度解析
            if base_strategy == ParseStrategy.STREAM_PARSE:
                return base_strategy
            return ParseStrategy.DEEP_PARSE
        else:
            # 超大文件使用流式解析
            return ParseStrategy.STREAM_PARSE

    @classmethod
    def _create_config(cls, strategy: ParseStrategy, file_size: int, mime_type: str) -> ParseConfig:
        """根据策略创建配置"""
        if strategy == ParseStrategy.QUICK_PARSE:
            return ParseConfig(
                strategy=strategy,
                chunk_size=512 * 1024,  # 512KB
                timeout=60,  # 1分钟
                max_workers=2
            )
        elif strategy == ParseStrategy.BALANCED_PARSE:
            return ParseConfig(
                strategy=strategy,
                chunk_size=1024 * 1024,  # 1MB
                timeout=180,  # 3分钟
                max_workers=4
            )
        elif strategy == ParseStrategy.DEEP_PARSE:
            return ParseConfig(
                strategy=strategy,
                chunk_size=2 * 1024 * 1024,  # 2MB
                timeout=600,  # 10分钟
                max_workers=2,
                memory_limit=1024 * 1024 * 1024  # 1GB
            )
        elif strategy == ParseStrategy.OCR_PARSE:
            is_chinese = 'ch' in mime_type or 'zh' in mime_type
            return ParseConfig(
                strategy=strategy,
                chunk_size=1024 * 1024,  # 1MB
                timeout=300,  # 5分钟
                enable_ocr=True,
                ocr_language='ch' if is_chinese else 'en',
                max_workers=1
            )
        elif strategy == ParseStrategy.STREAM_PARSE:
            return ParseConfig(
                strategy=strategy,
                chunk_size=10 * 1024 * 1024,  # 10MB
                timeout=1800,  # 30分钟
                max_workers=1,
                memory_limit=256 * 1024 * 1024  # 256MB
            )
        else:
            # 默认配置
            return ParseConfig(strategy=strategy)


# 简单测试
if __name__ == "__main__":
    import tempfile
    
    # 创建测试文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'A' * 1024 * 10)  # 10KB文件
        test_file = f.name
    
    try:
        selector = StrategySelector()
        config = selector.select_strategy(test_file, 'text/plain')
        print(f"文件: {test_file}")
        print(f"策略: {config.strategy.value}")
        print(f"块大小: {config.chunk_size}")
        print(f"超时: {config.timeout}")
        print(f"最大工作线程: {config.max_workers}")
    finally:
        os.unlink(test_file)