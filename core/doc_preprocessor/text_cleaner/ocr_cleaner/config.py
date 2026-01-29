"""
OCR专用清洗器配置类
定义OCR清洗器的配置选项
"""

class OCRCleanerConfig:
    """
    OCR专用清洗器配置类
    定义OCR清洗器的配置选项
    """
    
    def __init__(self):
        # OCR空格粘连修复配置
        self.fix_space_glue_errors = True  # 是否修复空格粘连错误
        self.merge_chinese_characters = True  # 是否合并中文字符间的空格
        self.merge_adjacent_digits = True  # 是否合并相邻数字间的空格
        self.merge_adjacent_letters = True  # 是否合并相邻字母间的空格
        
        # OCR字符错误纠正配置
        self.correct_ocr_errors = True  # 是否纠正OCR识别错误
        self.simple_mapping_correction = True  # 是否使用简单映射纠正
        self.context_aware_correction = True  # 是否使用上下文感知纠正
        
        # 其他配置
        self.enable_debug_logging = False  # 是否启用调试日志
        self.min_confidence_threshold = 0.5  # 最小置信度阈值，低于此值的元素会被特别处理