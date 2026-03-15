"""
集成测试脚本：测试整个文档预处理器的工作流程
该脚本将测试以下完整流程：
1. 格式路由分发模块接收文档
2. 解析器解析文档为Element对象
3. 清洗模块对Element进行清洗
4. 分块引擎将清洗后的内容分块
"""

import os
import json
from pathlib import Path

# 导入文档预处理器的各个组件
from core.doc_preprocessor.format_router.format_router import FormatRouter
from core.doc_preprocessor.format_router.task_queue import Priority
from core.doc_preprocessor.parsing_cluster.processor import DocumentParser, Element
from core.doc_preprocessor.text_cleaner.basic_cleaner import BasicTextCleaner
from core.doc_preprocessor.chunking_engine.engine import SmartChunkingEngine

# ElementType实际上是从Element类中获取的属性，而非独立的枚举
# 我们直接使用字符串值或者根据实际情况创建


def run_integration_test():
    """运行完整的集成测试"""
    print("="*60)
    print("开始文档预处理器集成测试")
    print("="*60)
    
    # 准备测试数据
    sample_doc_path = Path(__file__).parent / "sample_document.md"
    
    if not sample_doc_path.exists():
        raise FileNotFoundError(f"测试文档不存在: {sample_doc_path}")
    
    # 读取测试文档内容
    with open(sample_doc_path, 'r', encoding='utf-8') as f:
        document_content = f.read()
    
    print(f"✓ 加载测试文档: {sample_doc_path.name}")
    print(f"  文档长度: {len(document_content)} 字符")
    
    # 步骤1: 格式路由分发模块
    print("\n步骤1: 格式路由分发...")
    format_router = FormatRouter()
    
    # 使用FormatRouter的identify_and_route方法
    task_id = format_router.identify_and_route(
        file_path=str(sample_doc_path),
        user_id="test_user_001",
        team_id="test_team_001",
        priority=Priority.HIGH
    )
    print(f"  提交任务到路由，任务ID: {task_id}")
    
    # 获取队列状态
    queue_status = format_router.get_queue_status()
    print(f"  当前队列状态: {queue_status}")
    
    # 步骤2: 解析模块
    print("\n步骤2: 文档解析...")
    # 使用具体的解析器实现 - 根据文件类型选择合适的解析器
    from core.doc_preprocessor.parsing_cluster.markdown_parser import MarkdownParser
    
    parser = MarkdownParser()
    
    # 解析文档为Element对象
    # 注意：解析器的接口是parse(file_path, user_id, knowledge_base_id)
    result = parser.parse(str(sample_doc_path), "test_user_001", "test_team_001")
    elements_dict_list = result.get("elements", [])
    
    print(f"  解析完成，获得 {len(elements_dict_list)} 个Element对象")
    
    # 将字典列表转换回Element对象，因为其他组件需要Element对象
    from core.doc_preprocessor.parsing_cluster.processor import Element
    elements = []
    for elem_dict in elements_dict_list:
        element = Element(
            raw_content=elem_dict["raw_content"],
            element_type=elem_dict["element_type"],
            element_index=elem_dict["element_index"],
            source_format=elem_dict["source_format"],
            format_metadata=elem_dict.get("format_metadata", {}),
            parser_confidence=elem_dict.get("parser_confidence", 1.0)
        )
        elements.append(element)
    
    # 显示解析结果的简要信息
    for i, elem in enumerate(elements[:3]):  # 只显示前3个
        print(f"    [{i+1}] 类型: {elem.element_type}, 长度: {len(elem.raw_content)} 字符")
    
    if len(elements) > 3:
        print(f"    ... 还有 {len(elements) - 3} 个Element")
    
    # 步骤3: 清洗模块
    print("\n步骤3: 文本清洗...")
    cleaner = BasicTextCleaner()
    
    # BasicTextCleaner的clean方法接受Element对象列表
    cleaned_elements = cleaner.clean(elements)
    
    print(f"  清洗完成，处理了 {len(cleaned_elements)} 个Element")
    
    # 显示清洗结果的简要信息
    for i, elem in enumerate(cleaned_elements[:3]):  # 只显示前3个
        print(f"    [{i+1}] 类型: {elem.element_type}, 清洗后长度: {len(elem.raw_content)} 字符")
    
    # 步骤4: 分块引擎
    print("\n步骤4: 内容分块...")
    from core.doc_preprocessor.chunking_engine.engine import SmartChunkingEngine
    from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import ChunkConfig
    
    # 创建分块引擎配置
    config = ChunkConfig(default_chunk_size=200)
    chunking_engine = SmartChunkingEngine(config=config)
    
    # 使用分块引擎对Element进行分块
    chunk_result = chunking_engine.chunk_elements(
        elements=cleaned_elements,
        document_id="test_doc_001",
        team_id="test_team_001",
        user_id="test_user_001",
        file_name="sample_document.md",
        file_type="markdown",
        overlap_size=50
    )
    
    print(f"  分块完成，获得 {len(chunk_result.get('chunks', []))} 个文本块")
    
    # 显示分块结果的简要信息
    chunks = chunk_result.get('chunks', [])
    for i, chunk in enumerate(chunks[:3]):  # 只显示前3个
        print(f"    [{i+1}] 长度: {len(chunk.get('text', ''))} 字符, 类型: {chunk.get('element_type', 'unknown')}")
        print(f"         结构路径: {chunk.get('structure_path', [])}")
    
    if len(chunks) > 3:
        print(f"    ... 还有 {len(chunks) - 3} 个文本块")
    
    # 验证结果
    print("\n步骤5: 结果验证...")
    assert len(chunks) > 0, "应该至少有一个文本块"
    assert all('text' in chunk for chunk in chunks), "所有块都应该包含文本内容"
    assert all(len(chunk.get('text', '')) > 0 for chunk in chunks), "所有块的内容都不应为空"
    
    # 验证块大小是否符合预期
    oversized_chunks = [c for c in chunks if len(c.get('text', '')) > 250]  # 允许一些缓冲
    if oversized_chunks:
        print(f"  ⚠️  发现 {len(oversized_chunks)} 个可能过大的块")
    else:
        print("  ✓ 所有块的大小都在合理范围内")
    
    print(f"\n✓ 集成测试成功完成！")
    print(f"  总共处理了 {len(elements)} 个Element")
    print(f"  最终生成了 {len(chunks)} 个文本块")
    
    # 返回结果以便进一步分析
    return {
        "original_content_length": len(document_content),
        "parsed_elements_count": len(elements),
        "cleaned_elements": cleaned_elements,
        "chunks_count": len(chunks),
        "chunks": chunks,
        "chunk_result": chunk_result
    }


def run_additional_tests():
    """运行额外的测试场景"""
    print("\n" + "="*60)
    print("运行额外测试场景")
    print("="*60)
    
    # 场景1: 纯文本内容测试
    print("\n场景1: 纯文本内容测试...")
    text_content = """
    这是一个纯文本测试内容。
    
    包含多个段落和一些特殊字符：@#$%^&*()
    
    第二个段落包含更多的内容，用于测试解析器对长文本的处理能力。
    当文本变得很长时，分块引擎应该能够适当地将其分割成较小的部分。
    
    第三个段落用于测试段落间的连接和边界检测。
    """
    
    # 使用各组件处理纯文本
    cleaner = BasicTextCleaner()
    from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import ChunkConfig
    config = ChunkConfig(default_chunk_size=100)
    chunking_engine = SmartChunkingEngine(config=config)
    
    # 创建Element对象 - 使用正确的构造函数参数
    element = Element(
        raw_content=text_content.strip(),
        element_type="paragraph",
        element_index=0,
        source_format="text",
        format_metadata={"source": "integration_test", "position": 0}
    )
    
    # 清洗 - 需要将单个Element包装成列表
    cleaned_elements = cleaner.clean([element])
    cleaned_element = cleaned_elements[0]  # 获取第一个（也是唯一一个）元素
    print(f"  原始长度: {len(element.raw_content)}, 清洗后长度: {len(cleaned_element.raw_content)}")
    
    # 分块 - 使用正确的API
    chunk_result = chunking_engine.chunk_elements(
        elements=cleaned_elements,
        document_id="test_doc_002",
        team_id="test_team_001",
        user_id="test_user_001",
        file_name="text_test.txt",
        file_type="text",
        overlap_size=20
    )
    chunks = chunk_result.get('chunks', [])
    print(f"  分块数量: {len(chunks)}")
    
    # 场景2: 代码块测试
    print("\n场景2: 代码块内容测试...")
    code_content = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# 这是一个较长的函数注释，用于测试代码块的处理
# 注释内容可能会比较长，需要确保不会被错误地分割
result = fibonacci(10)
print(f"斐波那契数列第10项: {result}")
"""
    
    code_element = Element(
        raw_content=code_content.strip(),
        element_type="code_block",
        element_index=1,
        source_format="text",
        format_metadata={"source": "integration_test", "language": "python"}
    )
    
    cleaned_code_elements = cleaner.clean([code_element])
    code_chunk_result = chunking_engine.chunk_elements(
        elements=cleaned_code_elements,
        document_id="test_doc_003",
        team_id="test_team_001",
        user_id="test_user_001",
        file_name="code_test.py",
        file_type="code",
        overlap_size=20
    )
    code_chunks = code_chunk_result.get('chunks', [])
    print(f"  代码块分块数量: {len(code_chunks)}")
    
    print("\n✓ 额外测试场景完成")


def main():
    """主函数"""
    try:
        # 运行主要集成测试
        results = run_integration_test()
        
        # 运行额外测试场景
        run_additional_tests()
        
        print("\n" + "="*60)
        print("所有集成测试均已成功完成！")
        print("="*60)
        
        # 输出摘要信息
        print(f"处理摘要:")
        print(f"  - 原始文档长度: {results['original_content_length']} 字符")
        print(f"  - 解析得到元素数: {results['parsed_elements_count']}")
        print(f"  - 最终分块数: {results['chunks_count']}")
        
    except Exception as e:
        print(f"\n✗ 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 集成测试成功！文档预处理器各模块协同工作正常。")
    else:
        print("\n❌ 集成测试失败，请检查错误信息。")