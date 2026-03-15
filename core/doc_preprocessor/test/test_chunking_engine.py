"""
智能分块引擎测试用例
"""
import unittest
import json
from core.doc_preprocessor.chunking_engine.engine import SmartChunkingEngine
from core.doc_preprocessor.chunking_engine.chunk import Chunk, format_chunks_for_output
from core.doc_preprocessor.chunking_engine.boundary_detector.detector import (
    BoundaryDetectorFactory, MarkdownBoundaryDetector, 
    GenericTextBoundaryDetector, BoundaryType
)
from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import (
    AdaptiveChunkerFactory, CodeBlockChunker, TableChunker, 
    ParagraphChunker, FixedSizeChunker, ChunkConfig
)
from core.doc_preprocessor.chunking_engine.overlap_controller.controller import (
    SimpleOverlapController, SemanticOverlapController, OverlapControllerFactory
)
from core.doc_preprocessor.parsing_cluster.processor import Element


class TestBoundaryDetector(unittest.TestCase):
    """边界检测器测试"""
    
    def setUp(self):
        self.factory = BoundaryDetectorFactory()
    
    def test_markdown_boundary_detection(self):
        """测试Markdown边界检测"""
        detector = self.factory.get_detector('markdown')
        text = """# 标题1
这是第一段内容

## 标题2
- 列表项1
- 列表项2

```python
print('代码块')
```

普通段落内容。
"""
        boundaries = detector.detect_boundaries(text, 'markdown')
        
        # 应该检测到标题、列表和代码块边界
        heading_boundaries = [b for b in boundaries if b.type == BoundaryType.HEADING]
        list_boundaries = [b for b in boundaries if b.type == BoundaryType.LIST_ITEM]
        code_boundaries = [b for b in boundaries if b.type == BoundaryType.CODE_BLOCK]
        
        self.assertGreaterEqual(len(heading_boundaries), 2, "应该检测到至少2个标题边界")
        self.assertGreaterEqual(len(list_boundaries), 2, "应该检测到至少2个列表边界")
        self.assertGreaterEqual(len(code_boundaries), 1, "应该检测到至少1个代码块边界")
    
    def test_generic_text_boundary_detection(self):
        """测试通用文本边界检测"""
        detector = GenericTextBoundaryDetector()
        text = """第一段内容


第二段内容
  缩进内容
* 项目符号
  继续缩进
"""
        boundaries = detector.detect_boundaries(text)
        
        # 应该检测到段落和缩进边界
        paragraph_boundaries = [b for b in boundaries if b.type == BoundaryType.PARAGRAPH]
        indent_boundaries = [b for b in boundaries if b.type == BoundaryType.SECTION]
        list_boundaries = [b for b in boundaries if b.type == BoundaryType.LIST_ITEM]
        
        self.assertGreaterEqual(len(paragraph_boundaries), 1, "应该检测到段落边界")


class TestAdaptiveChunker(unittest.TestCase):
    """自适应分块器测试"""
    
    def setUp(self):
        self.factory = AdaptiveChunkerFactory()
    
    def test_code_block_chunking(self):
        """测试代码块分块"""
        chunker = self.factory.get_chunker('code_block')
        config = ChunkConfig()
        
        # 长代码块应该被分割
        long_code = '\n'.join([f'# 这是第{i}行代码' for i in range(100)])
        chunks = chunker.chunk(long_code, 'code_block', 'python', config)
        
        # 至少会生成一个块
        self.assertGreaterEqual(len(chunks), 1, "应该生成至少一个代码块")
        
        # 短代码块应该保持完整
        short_code = "print('hello world')"
        chunks = chunker.chunk(short_code, 'code_block', 'python', config)
        
        self.assertEqual(len(chunks), 1, "短代码块应该保持完整")
        self.assertEqual(chunks[0]['text'], short_code, "代码内容应该保持不变")
    
    def test_paragraph_chunking(self):
        """测试段落分块"""
        chunker = self.factory.get_chunker('paragraph')
        config = ChunkConfig(paragraph_chunk_size=50, min_paragraph_chunk_size=20)
        
        # 长段落应该被分割
        long_para = "这是一个很长的段落。" * 20  # 重复20次
        chunks = chunker.chunk(long_para, 'paragraph', 'text', config)
        
        self.assertGreaterEqual(len(chunks), 2, "长段落应该被分割成多个块")
        
        # 检查块大小是否合理
        for chunk in chunks[:-1]:  # 除了最后一个块
            self.assertLessEqual(len(chunk['text']), config.paragraph_chunk_size + 20, 
                               "块大小应该接近但不超过限制")


class TestOverlapController(unittest.TestCase):
    """重叠控制器测试"""
    
    def setUp(self):
        self.simple_controller = SimpleOverlapController()
        self.semantic_controller = SemanticOverlapController()
    
    def test_simple_overlap(self):
        """测试简单重叠"""
        chunks = [
            {"text": "第一块内容", "chunk_index": 0, "element_type": "paragraph"},
            {"text": "第二块内容", "chunk_index": 1, "element_type": "paragraph"},
            {"text": "第三块内容", "chunk_index": 2, "element_type": "paragraph"}
        ]
        
        overlapped_chunks = self.simple_controller.apply_overlap(chunks, overlap_size=3)
        
        # 检查是否添加了重叠信息
        for i, chunk in enumerate(overlapped_chunks):
            if i > 0:
                self.assertIn('overlap_prefix', chunk, "后续块应该有重叠前缀")
            if i < len(overlapped_chunks) - 1:
                self.assertIn('overlap_suffix', chunk, "非最后块应该有重叠后缀")
    
    def test_semantic_overlap(self):
        """测试语义重叠"""
        chunks = [
            {"text": "这是第一句话。这是第二句话。", "chunk_index": 0, "element_type": "paragraph"},
            {"text": "这是第三句话？这是第四句话！", "chunk_index": 1, "element_type": "paragraph"}
        ]
        
        overlapped_chunks = self.semantic_controller.apply_overlap(chunks, overlap_size=10)
        
        self.assertEqual(len(overlapped_chunks), 2, "块的数量应该保持不变")


class TestChunkClass(unittest.TestCase):
    """Chunk类测试"""
    
    def test_chunk_creation_and_serialization(self):
        """测试Chunk对象的创建和序列化"""
        chunk = Chunk(
            text="测试内容",
            chunk_index=0,
            structure_path=["# 主标题", "## 子标题"],
            element_type="paragraph",
            metadata={"size": 100}
        )
        
        # 测试序列化
        chunk_dict = chunk.to_dict()
        self.assertEqual(chunk_dict['text'], "测试内容")
        self.assertEqual(chunk_dict['chunk_index'], 0)
        self.assertEqual(chunk_dict['structure_path'], ["# 主标题", "## 子标题"])
        self.assertEqual(chunk_dict['element_type'], "paragraph")
        self.assertEqual(chunk_dict['metadata'], {"size": 100})
        
        # 测试反序列化
        reconstructed = Chunk.from_dict(chunk_dict)
        self.assertEqual(reconstructed.text, chunk.text)
        self.assertEqual(reconstructed.chunk_index, chunk.chunk_index)
    
    def test_format_chunks_for_output(self):
        """测试格式化输出"""
        chunks = [
            Chunk(text="内容1", chunk_index=0),
            Chunk(text="内容2", chunk_index=1, structure_path=["# 标题"])
        ]
        
        result = format_chunks_for_output(
            chunks=chunks,
            document_id="doc_001",
            team_id="team_abc",
            user_id="user_1234",
            file_name="测试文档.md",
            file_type="markdown"
        )
        
        self.assertEqual(result['document_id'], "doc_001")
        self.assertEqual(result['file_type'], "markdown")
        self.assertEqual(len(result['chunks']), 2)
        self.assertEqual(result['chunks'][0]['text'], "内容1")


class TestSmartChunkingEngine(unittest.TestCase):
    """智能分块引擎测试"""
    
    def setUp(self):
        self.engine = SmartChunkingEngine()
    
    def test_chunk_elements(self):
        """测试对Element列表进行分块"""
        elements = [
            Element(
                raw_content="这是第一个段落的内容。" * 10,
                element_type="paragraph",
                element_index=0,
                source_format="text",
                format_metadata={},
                parser_confidence=0.9
            ),
            Element(
                raw_content="# 标题\n这是标题下的内容。",
                element_type="heading",
                element_index=1,
                source_format="markdown",
                format_metadata={},
                parser_confidence=1.0
            )
        ]
        
        result = self.engine.chunk_elements(
            elements=elements,
            document_id="doc_001",
            team_id="team_abc",
            user_id="user_1234",
            file_name="测试文档.md",
            file_type="markdown"
        )
        
        self.assertEqual(result['document_id'], "doc_001")
        self.assertEqual(result['file_type'], "markdown")
        self.assertGreaterEqual(len(result['chunks']), 1, "应该生成至少一个分块")
        
        # 检查每个分块都有必需的字段
        for chunk in result['chunks']:
            self.assertIn('text', chunk, "每个分块都应该有text字段")
            self.assertIn('chunk_index', chunk, "每个分块都应该有chunk_index字段")
    
    def test_chunk_text_with_structure_detection(self):
        """测试带结构检测的文本分块"""
        text = """# 主标题
这是第一段内容。

## 子标题
- 列表项1
- 列表项2

```python
# 代码示例
def hello():
    print('Hello, World!')
```

最后一段内容。
"""
        
        result = self.engine.chunk_text_with_structure_detection(
            text=text,
            file_type="markdown",
            document_id="doc_002",
            team_id="team_abc",
            user_id="user_5678",
            file_name="结构测试.md"
        )
        
        self.assertEqual(result['document_id'], "doc_002")
        self.assertGreaterEqual(len(result['chunks']), 1, "应该生成至少一个分块")
        
        # 检查是否正确识别了结构
        has_structure_path = any('structure_path' in chunk and chunk['structure_path'] 
                                for chunk in result['chunks'])
        self.assertTrue(has_structure_path, "应该包含结构路径信息")


def run_all_tests():
    """运行所有测试"""
    test_classes = [
        TestBoundaryDetector,
        TestAdaptiveChunker,
        TestOverlapController,
        TestChunkClass,
        TestSmartChunkingEngine
    ]
    
    for test_class in test_classes:
        print(f"\n运行 {test_class.__name__} 测试...")
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if result.failures or result.errors:
            print(f"❌ {test_class.__name__} 中有失败的测试")
            for failure in result.failures:
                print(f"  失败: {failure[0]}")
                print(f"    {str(failure[1]).split(chr(10))[0]}")
            for error in result.errors:
                print(f"  错误: {error[0]}")
                print(f"    {str(error[1]).split(chr(10))[0]}")
        else:
            print(f"✅ {test_class.__name__} 所有测试通过!")


if __name__ == '__main__':
    run_all_tests()