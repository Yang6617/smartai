"""
智能分块引擎使用示例
展示如何使用智能分块引擎对文档进行分块处理
"""
from core.doc_preprocessor.chunking_engine.engine import SmartChunkingEngine
from core.doc_preprocessor.chunking_engine.chunk import Chunk, format_chunks_for_output
from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import ChunkConfig
from core.doc_preprocessor.parsing_cluster.processor import Element


def demonstrate_basic_chunking():
    """演示基本分块功能"""
    print("智能分块引擎使用示例")
    print("=" * 50)
    
    # 创建分块引擎实例
    engine = SmartChunkingEngine()
    
    # 示例1: 对Element列表进行分块
    print("\n1. 对Element列表进行分块:")
    elements = [
        Element(
            raw_content="这是第一个段落的内容，它包含了很多信息，需要被适当地分块处理。" * 5,
            element_type="paragraph",
            element_index=0,
            source_format="text",
            format_metadata={},
            parser_confidence=0.85
        ),
        Element(
            raw_content="# 主标题\n这是标题下的内容，描述了一些重要的概念。",
            element_type="heading",
            element_index=1,
            source_format="markdown",
            format_metadata={},
            parser_confidence=0.95
        ),
        Element(
            raw_content="```python\n# 代码块示例\ndef hello():\n    print('Hello, World!')\n```",
            element_type="code_block",
            element_index=2,
            source_format="markdown",
            format_metadata={},
            parser_confidence=0.90
        )
    ]
    
    result = engine.chunk_elements(
        elements=elements,
        document_id="doc_001",
        team_id="team_abc",
        user_id="user_1234",
        file_name="示例文档.md",
        file_type="markdown"
    )
    
    print(f"文档: {result['file_name']}")
    print(f"文件类型: {result['file_type']}")
    print(f"分块数量: {len(result['chunks'])}")
    print("\n分块详情:")
    for i, chunk in enumerate(result['chunks']):
        print(f"  块 {i}: {chunk['text'][:50]}..." if len(chunk['text']) > 50 else f"  块 {i}: {chunk['text']}")
        print(f"    类型: {chunk.get('element_type', 'unknown')}")
        print(f"    索引: {chunk['chunk_index']}")
        if 'structure_path' in chunk and chunk['structure_path']:
            print(f"    结构路径: {chunk['structure_path']}")


def demonstrate_advanced_chunking():
    """演示高级分块功能"""
    print("\n" + "=" * 50)
    print("2. 高级分块功能演示 - 结构感知分块:")
    
    # 创建带有自定义配置的引擎
    config = ChunkConfig(
        default_chunk_size=100,
        paragraph_chunk_size=150,
        preserve_code_blocks=True,
        include_headers_in_chunks=True
    )
    engine = SmartChunkingEngine(config=config)
    
    # 示例Markdown文本，包含多种结构
    markdown_text = """# 人工智能概述

人工智能(AI)是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

## 机器学习

机器学习是人工智能的一个重要分支。它致力于研究如何使机器具备学习能力。

### 监督学习

监督学习是最常见的机器学习类型。它使用标记的数据集来训练模型。

- 优点：准确性高
- 缺点：需要大量标记数据

### 无监督学习

无监督学习试图从未标记的数据中发现隐藏的结构。

```python
# 这是一段示例代码
def ml_algorithm(data):
    processed = []
    for item in data:
        processed.append(item * 2)
    return processed
```

## 深度学习

深度学习是机器学习的一个子集，它模仿人脑的工作方式来创建神经网络。

总的来说，人工智能技术正在快速发展，为各行各业带来了巨大的变革。
"""
    
    result = engine.chunk_text_with_structure_detection(
        text=markdown_text,
        file_type="markdown",
        document_id="doc_002",
        team_id="team_xyz",
        user_id="user_5678",
        file_name="AI_Overview.md",
        overlap_size=30  # 设置重叠大小
    )
    
    print(f"文档: {result['file_name']}")
    print(f"分块数量: {len(result['chunks'])}")
    print("\n结构感知分块详情:")
    for i, chunk in enumerate(result['chunks']):
        print(f"\n  块 {i} (索引: {chunk['chunk_index']}):")
        print(f"    内容预览: {chunk['text'][:60]}..." if len(chunk['text']) > 60 else f"    内容: {chunk['text']}")
        if 'structure_path' in chunk and chunk['structure_path']:
            print(f"    结构路径: {' -> '.join(chunk['structure_path'])}")
        if 'element_type' in chunk:
            print(f"    元素类型: {chunk['element_type']}")
        if 'metadata' in chunk and chunk['metadata']:
            print(f"    元数据: {chunk['metadata']}")


def demonstrate_configuration_options():
    """演示配置选项"""
    print("\n" + "=" * 50)
    print("3. 配置选项演示:")
    
    # 不同的配置选项
    config1 = ChunkConfig(
        default_chunk_size=200,
        preserve_code_blocks=True,
        table_chunk_strategy="whole"
    )
    
    engine1 = SmartChunkingEngine(config=config1)
    
    print("配置选项:")
    print(f"  - 默认分块大小: {config1.default_chunk_size}")
    print(f"  - 保持代码块完整: {config1.preserve_code_blocks}")
    print(f"  - 表格分块策略: {config1.table_chunk_strategy}")
    
    # 示例文本
    sample_text = "这是用于演示配置选项的文本。" * 10
    result = engine1.chunk_text_with_structure_detection(
        text=sample_text,
        file_type="text",
        document_id="doc_003",
        team_id="team_def",
        user_id="user_9012",
        file_name="配置示例.txt"
    )
    
    print(f"\n使用上述配置处理文本后生成 {len(result['chunks'])} 个分块")


def demonstrate_json_output():
    """演示JSON输出格式"""
    print("\n" + "=" * 50)
    print("4. JSON输出格式演示:")
    
    # 创建一些示例分块
    chunks = [
        Chunk(
            text="我们的产品支持实时协作...",
            chunk_index=0,
            structure_path=["# 功能特色", "## 核心优势"],
            element_type="paragraph",
            metadata={"length": 12, "word_count": 6}
        ),
        Chunk(
            text="# 性能优化\n系统经过深度优化...",
            chunk_index=1,
            structure_path=["# 性能优化"],
            element_type="heading",
            metadata={"length": 25, "word_count": 8}
        )
    ]
    
    # 格式化为JSON输出
    json_output = format_chunks_for_output(
        chunks=chunks,
        document_id="doc_001",
        team_id="team_abc",
        user_id="user_1234",
        file_name="产品介绍.md",
        file_type="markdown"
    )
    
    import json
    formatted_json = json.dumps(json_output, ensure_ascii=False, indent=2)
    print("符合要求的JSON输出格式:")
    print(formatted_json)


if __name__ == "__main__":
    demonstrate_basic_chunking()
    demonstrate_advanced_chunking()
    demonstrate_configuration_options()
    demonstrate_json_output()
    
    print("\n" + "=" * 50)
    print("智能分块引擎演示完成!")