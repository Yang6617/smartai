"""
验证文本清洗模块的整体功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        from core.doc_preprocessor.text_cleaner import BasicTextCleaner, TextCleanerConfig
        print("  ✅ 成功导入 BasicTextCleaner 和 TextCleanerConfig")
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False
    
    try:
        from core.doc_preprocessor.text_cleaner import get_default_config, get_aggressive_config, get_light_config
        print("  ✅ 成功导入配置函数")
    except ImportError as e:
        print(f"  ❌ 导入配置函数失败: {e}")
        return False
    
    return True

def test_basic_functionality():
    """测试基本功能"""
    print("\n测试基本功能...")
    
    try:
        from core.doc_preprocessor.text_cleaner import BasicTextCleaner, TextCleanerConfig
        from core.doc_preprocessor.text_cleaner import get_default_config, get_aggressive_config, get_light_config
        
        # 创建清洗器
        cleaner = BasicTextCleaner()
        print("  ✅ 成功创建 BasicTextCleaner 实例")
        
        # 创建配置
        config = TextCleanerConfig()
        print("  ✅ 成功创建 TextCleanerConfig 实例")
        
        # 测试预设配置
        default_cfg = get_default_config()
        aggressive_cfg = get_aggressive_config()
        light_cfg = get_light_config()
        print("  ✅ 成功获取预设配置")
        
    except Exception as e:
        print(f"  ❌ 功能测试失败: {e}")
        return False
    
    return True

def test_simple_clean():
    """测试简单清洗功能"""
    print("\n测试简单清洗功能...")
    
    try:
        from core.doc_preprocessor.parsing_cluster.processor import Element
        from core.doc_preprocessor.text_cleaner import BasicTextCleaner
        
        # 创建测试Element
        test_element = Element(
            raw_content="  全角空格　　和ＡＢＣ字符  ",
            element_type="paragraph",
            element_index=0,
            source_format="text",
            format_metadata={},
            parser_confidence=0.9
        )
        
        # 创建清洗器并执行清洗
        cleaner = BasicTextCleaner()
        cleaned_elements = cleaner.clean([test_element])
        
        if len(cleaned_elements) == 1:
            print("  ✅ 成功清洗单个Element")
            print(f"     原始内容: {repr(test_element.raw_content)}")
            print(f"     清洗后:   {repr(cleaned_elements[0].raw_content)}")
        else:
            print("  ❌ 清洗结果数量不正确")
            return False
            
    except Exception as e:
        print(f"  ❌ 清洗功能测试失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("="*60)
    print("文本清洗模块整体功能验证")
    print("="*60)
    
    all_passed = True
    
    # 测试导入
    all_passed &= test_imports()
    
    # 测试基本功能
    all_passed &= test_basic_functionality()
    
    # 测试清洗功能
    all_passed &= test_simple_clean()
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有验证通过！文本清洗模块功能正常。")
    else:
        print("❌ 验证失败！")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)