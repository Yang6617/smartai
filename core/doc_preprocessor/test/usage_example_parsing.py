"""
解析集群使用示例
展示如何使用文档解析框架处理不同格式的文档
"""

import os
import tempfile
from core.doc_preprocessor.parsing_cluster import DocumentProcessor, MarkdownParser, PlainTextParser, DocPreprocessorConfig


def main():
    """主函数 - 演示如何使用文档处理器"""
    print("文档解析集群使用示例\n")
    
    # 创建文档处理器
    processor = DocumentProcessor()
    
    # 创建并注册不同的解析器
    text_parser = PlainTextParser()
    markdown_parser = MarkdownParser()
    
    processor.register_parser(text_parser)
    processor.register_parser(markdown_parser)
    
    # 显示支持的格式
    print("支持的文件格式:", processor.get_supported_formats())
    
    # 创建测试Markdown内容
    test_md_content = """# 产品介绍
这是产品的总体介绍。

## 功能特点
- 特点1：高性能
- 特点2：易用性
- 特点3：可扩展性

### 技术细节
```python
def feature_example():
    return "This is an example"
```

> 这是一个引用块
"""

    # 创建临时Markdown文件进行演示
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(test_md_content)
        md_file_path = f.name

    try:
        print(f"\n处理Markdown文件: {os.path.basename(md_file_path)}")
        
        # 处理文档
        result = processor.process_document(md_file_path, "user123", "team456")
        
        print(f"用户ID: {result['user_id']}")
        print(f"知识库ID: {result['knowledge_base_id']}")
        print(f"文件名: {result['file_name']}")
        print(f"总元素数: {len(result['elements'])}")
        
        print("\n解析出的元素类型分布:")
        element_types = [elem['element_type'] for elem in result['elements']]
        type_counts = {}
        for et in element_types:
            type_counts[et] = type_counts.get(et, 0) + 1
        
        for elem_type, count in type_counts.items():
            print(f"  {elem_type}: {count}")
        
        print("\n前5个元素详情:")
        for i, elem in enumerate(result['elements'][:5]):
            print(f"  {i+1}. [{elem['element_type']}] {elem['raw_content'][:50]}{'...' if len(elem['raw_content']) > 50 else ''}")
    
    finally:
        # 清理临时文件
        os.unlink(md_file_path)
    
    print("\n解析集群可以轻松扩展以支持更多文档格式，只需实现DocumentParser接口即可。")


if __name__ == "__main__":
    main()