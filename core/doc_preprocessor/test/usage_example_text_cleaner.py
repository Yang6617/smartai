"""
文本清洗模块使用示例
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.doc_preprocessor.parsing_cluster.processor import Element
from core.doc_preprocessor.text_cleaner.basic_cleaner import BasicTextCleaner
from core.doc_preprocessor.text_cleaner.config import TextCleanerConfig


def main():
    """主函数 - 演示文本清洗器的使用"""
    print("文本清洗模块使用示例\n")
    
    # 创建一些测试用的Element对象
    test_elements = [
        Element(
            raw_content="  这是一个　　包含全角空格和　连续空格的文本。  ",
            element_type="paragraph",
            element_index=0,
            source_format="text",
            format_metadata={"language": "zh"},
            parser_confidence=0.9
        ),
        Element(
            raw_content="这是包含全角字符ＡＢＣＤＥＦ的文本。\r\n包含\r多种换行符。\n\n\n\n过多的换行符。",
            element_type="paragraph", 
            element_index=1,
            source_format="text",
            format_metadata={"language": "zh"},
            parser_confidence=0.85
        ),
        Element(
            raw_content="这段文本包含乱码字符Â和Ê等。",
            element_type="paragraph",
            element_index=2,
            source_format="text", 
            format_metadata={"language": "zh"},
            parser_confidence=0.8
        )
    ]
    
    print("原始Element内容:")
    for i, elem in enumerate(test_elements):
        print(f"  {i+1}. [{elem.element_type}] {repr(elem.raw_content)}")
    
    print("\n" + "="*60)
    
    # 创建基础清洗器
    cleaner = BasicTextCleaner()
    
    # 执行清洗
    cleaned_elements = cleaner.clean(test_elements)
    
    print("清洗后的Element内容:")
    for i, elem in enumerate(cleaned_elements):
        print(f"  {i+1}. [{elem.element_type}] {repr(elem.raw_content)}")
    
    print(f"\n清洗器信息: {cleaner.get_cleaner_info()}")
    
    print("\n" + "="*60)
    
    # 使用自定义配置
    print("使用自定义配置进行清洗...")
    custom_config = TextCleanerConfig()
    custom_config.max_consecutive_newlines = 1  # 只保留1个连续换行符
    custom_config.fix_common_mojibake = True
    custom_config.normalize_full_width_chars = True
    
    custom_cleaner = BasicTextCleaner(custom_config)
    custom_cleaned_elements = custom_cleaner.clean(test_elements)
    
    print("自定义配置清洗后的Element内容:")
    for i, elem in enumerate(custom_cleaned_elements):
        print(f"  {i+1}. [{elem.element_type}] {repr(elem.raw_content)}")
    
    print(f"\n自定义清洗器信息: {custom_cleaner.get_cleaner_info()}")
    
    print("\n文本清洗模块演示完成！")


if __name__ == "__main__":
    main()