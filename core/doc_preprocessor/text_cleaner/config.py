"""
文本清洗器配置管理
定义文本清洗器的各种配置选项
"""

from typing import Dict, Any, Optional


class TextCleanerConfig:
    """
    文本清洗器配置类
    定义清洗器的配置选项
    """
    
    def __init__(self):
        # 空白字符标准化配置
        self.normalize_whitespace = True  # 是否标准化空白字符
        self.remove_leading_trailing = True  # 是否去除首尾空白
        self.convert_full_width_spaces = True  # 是否转换全角空格
        self.merge_consecutive_spaces = True  # 是否合并连续空格
        
        # 编码规范化配置
        self.normalize_full_width_chars = True  # 是否转换全角字符
        self.fix_common_mojibake = True  # 是否修复常见乱码
        self.unify_punctuation = True  # 是否统一标点符号
        
        # 换行符统一配置
        self.normalize_line_breaks = True  # 是否统一换行符
        self.max_consecutive_newlines = 2  # 最大连续换行符数量
        
        # 其他配置
        self.preserve_special_chars = []  # 需要保留的特殊字符列表
        self.enable_debug_logging = False  # 是否启用调试日志
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        从字典更新配置
        
        Args:
            config_dict: 配置字典
        """
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将配置转换为字典
        
        Returns:
            配置字典
        """
        return {
            'normalize_whitespace': self.normalize_whitespace,
            'remove_leading_trailing': self.remove_leading_trailing,
            'convert_full_width_spaces': self.convert_full_width_spaces,
            'merge_consecutive_spaces': self.merge_consecutive_spaces,
            'normalize_full_width_chars': self.normalize_full_width_chars,
            'fix_common_mojibake': self.fix_common_mojibake,
            'unify_punctuation': self.unify_punctuation,
            'normalize_line_breaks': self.normalize_line_breaks,
            'max_consecutive_newlines': self.max_consecutive_newlines,
            'preserve_special_chars': self.preserve_special_chars,
            'enable_debug_logging': self.enable_debug_logging
        }
    
    def copy(self) -> 'TextCleanerConfig':
        """
        创建配置的副本
        
        Returns:
            配置副本
        """
        new_config = TextCleanerConfig()
        new_config.update_from_dict(self.to_dict())
        return new_config


def get_default_config() -> TextCleanerConfig:
    """
    获取默认配置
    
    Returns:
        默认配置对象
    """
    return TextCleanerConfig()


def get_aggressive_config() -> TextCleanerConfig:
    """
    获取激进清洗配置（更严格的清洗）
    
    Returns:
        激进清洗配置对象
    """
    config = TextCleanerConfig()
    config.normalize_whitespace = True
    config.remove_leading_trailing = True
    config.convert_full_width_spaces = True
    config.merge_consecutive_spaces = True
    config.normalize_full_width_chars = True
    config.fix_common_mojibake = True
    config.unify_punctuation = True
    config.normalize_line_breaks = True
    config.max_consecutive_newlines = 1  # 更严格的换行符控制
    return config


def get_light_config() -> TextCleanerConfig:
    """
    获取轻量清洗配置（较少的清洗）
    
    Returns:
        轻量清洗配置对象
    """
    config = TextCleanerConfig()
    config.normalize_whitespace = True
    config.remove_leading_trailing = True
    config.normalize_line_breaks = True
    config.max_consecutive_newlines = 2
    # 其他选项保持关闭以减少清洗强度
    config.convert_full_width_spaces = False
    config.normalize_full_width_chars = False
    config.fix_common_mojibake = False
    config.unify_punctuation = False
    return config