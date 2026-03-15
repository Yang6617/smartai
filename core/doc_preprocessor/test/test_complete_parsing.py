"""
全面测试解析集群功能
"""

import sys
import os
import tempfile

# 添加项目根目录到路径
from pathlib import Path
sys.path.insert(0, str((Path(__file__).parent).resolve()))

from core.doc_preprocessor.parsing_cluster import DocumentProcessor, MarkdownParser, PlainTextParser


def test_complete_workflow():
    """测试完整的解析工作流程"""
    print("测试完整的解析工作流程...")
    
    # 创建文档处理器
    processor = DocumentProcessor()
    
    # 注册解析器
    text_parser = PlainTextParser()
    markdown_parser = MarkdownParser()
    
    processor.register_parser(text_parser)
    processor.register_parser(markdown_parser)
    
    print(f"✓ 已注册解析器，支持格式: {processor.get_supported_formats()}")
    
    # 测试1: Markdown文件解析
    test_md_content = """# 标题1
这是第一段内容。

## 标题2
- 列表项1
- 列表项2

```python
def code_example():
    return "Hello"
```

> 这是引用内容
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(test_md_content)
        md_file_path = f.name

    try:
        print(f"\n处理Markdown文件...")
        md_result = processor.process_document(md_file_path, "user123", "team456")
        
        assert md_result['user_id'] == "user123"
        assert md_result['knowledge_base_id'] == "team456"
        assert len(md_result['elements']) > 0
        
        # 验证元素类型分布
        element_types = [elem['element_type'] for elem in md_result['elements']]
        expected_types = {'heading', 'paragraph', 'list_item', 'code_block', 'blockquote'}
        actual_types = set(element_types)
        
        assert expected_types.issubset(actual_types), f"缺少期望的元素类型: {expected_types - actual_types}"
        
        print(f"✓ Markdown解析完成，共生成 {len(md_result['elements'])} 个元素")
        print(f"  元素类型: {list(set(element_types))}")
        
    finally:
        os.unlink(md_file_path)
    
    # 测试2: 文本文件解析
    test_txt_content = """第一行文本内容
第二行文本内容
第三行文本内容"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_txt_content)
        txt_file_path = f.name

    try:
        print(f"\n处理文本文件...")
        txt_result = processor.process_document(txt_file_path, "user456", "team789")
        
        assert txt_result['user_id'] == "user456"
        assert txt_result['knowledge_base_id'] == "team789"
        assert len(txt_result['elements']) > 0
        
        # 验证文本文件解析的元素类型
        txt_element_types = [elem['element_type'] for elem in txt_result['elements']]
        print(f"✓ 文本解析完成，共生成 {len(txt_result['elements'])} 个元素")
        print(f"  元素类型: {list(set(txt_element_types))}")
        
    finally:
        os.unlink(txt_file_path)
    
    print("\n✓ 完整工作流程测试通过")


def test_element_structure():
    """测试Element对象结构"""
    print("\n测试Element对象结构...")
    
    from core.doc_preprocessor.parsing_cluster import Element
    
    # 创建一个Element对象
    element = Element(
        raw_content="测试内容",
        element_type="paragraph",
        element_index=0,
        source_format="markdown",
        format_metadata={"detected_language": "zh-CN"},
        parser_confidence=0.95
    )
    
    element_dict = element.to_dict()
    
    # 验证必需字段
    required_fields = ['element_id', 'raw_content', 'element_type', 'element_index', 'source_format', 'format_metadata', 'parser_confidence']
    for field in required_fields:
        assert field in element_dict, f"缺少必需字段: {field}"
    
    # 验证不包含可选字段
    optional_fields = ['raw_position', 'parent_references']
    for field in optional_fields:
        assert field not in element_dict, f"不应包含可选字段: {field}"
    
    print("✓ Element对象结构测试通过")


def main():
    """主函数"""
    print("开始全面测试解析集群...\n")
    
    try:
        test_element_structure()
        test_complete_workflow()
        
        print("\n" + "="*60)
        print("所有测试通过！解析集群功能完整。")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    main()