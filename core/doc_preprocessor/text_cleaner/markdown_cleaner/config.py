"""
Markdown专用清洗器配置类
定义Markdown清洗器的配置选项
"""

class MarkdownCleanerConfig:
    """
    Markdown专用清洗器配置类
    定义Markdown清洗器的配置选项
    """
    
    def __init__(self):
        # 标题处理配置
        self.normalize_heading_format = True  # 是否规范化标题格式
        self.remove_extra_heading_hashes = True  # 是否移除标题末尾多余的#号
        self.ensure_space_after_heading_marker = True  # 确保#后有空格
        
        # 代码块处理配置
        self.preserve_code_block_formatting = True  # 是否保留代码块内部格式
        self.normalize_code_fence_spacing = True  # 是否规范化代码围栏外部空格
        
        # 列表处理配置
        self.normalize_list_markers = True  # 是否规范化列表标记
        self.consistent_list_spacing = True  # 是否保持列表间距一致
        
        # 链接处理配置
        self.fix_link_spacing = True  # 是否修复链接中的多余空格
        
        # 其他配置
        self.enable_debug_logging = False  # 是否启用调试日志