"""
自适应分块器
根据内容类型调整分块策略
"""
import re
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class ChunkStrategy(Enum):
    """分块策略枚举"""
    FIXED_SIZE = "fixed_size"  # 固定大小分块
    SEMANTIC_BOUNDARY = "semantic_boundary"  # 语义边界分块
    PRESERVE_BLOCK = "preserve_block"  # 保持块完整
    ADAPTIVE = "adaptive"  # 自适应分块


@dataclass
class ChunkConfig:
    """分块配置类"""
    # 默认分块大小（token数或字符数）
    default_chunk_size: int = 500
    
    # 代码块特殊配置
    code_chunk_size: int = 2000  # 代码块可以更大
    preserve_code_blocks: bool = True  # 是否保持代码块完整
    
    # 表格特殊配置
    table_chunk_strategy: str = "row_split"  # 表格分块策略："whole", "row_split", "column_split"
    table_max_rows_per_chunk: int = 20  # 每个块的最大行数
    
    # 段落特殊配置
    paragraph_chunk_size: int = 500  # 段落分块大小
    min_paragraph_chunk_size: int = 100  # 段落最小分块大小
    
    # 标题处理配置
    include_headers_in_chunks: bool = True  # 是否在块中包含标题信息
    header_hierarchy_tracking: bool = True  # 是否跟踪标题层级
    
    # 语义边界敏感度
    semantic_boundary_sensitivity: float = 0.8  # 语义边界敏感度（0-1）


class AdaptiveChunker(ABC):
    """自适应分块器抽象基类"""
    
    @abstractmethod
    def chunk(self, text: str, element_type: str, file_type: str, config: ChunkConfig = None) -> List[Dict[str, Any]]:
        """
        根据内容类型进行自适应分块
        
        Args:
            text: 待分块的文本
            element_type: 元素类型
            file_type: 文件类型
            config: 分块配置
            
        Returns:
            分块结果列表
        """
        pass


class CodeBlockChunker(AdaptiveChunker):
    """代码块分块器"""
    
    def chunk(self, text: str, element_type: str, file_type: str, config: ChunkConfig = None) -> List[Dict[str, Any]]:
        """
        代码块分块逻辑
        代码块通常保持完整，不进行分割
        """
        if config is None:
            config = ChunkConfig()
        
        chunks = []
        
        # 如果需要保持代码块完整
        if config.preserve_code_blocks:
            # 对于特别大的代码块，按行进行分割
            lines = text.split('\n')
            if len(text) > config.code_chunk_size and len(lines) > 10:
                # 按行分割大代码块
                current_chunk_lines = []
                current_size = 0
                
                for line in lines:
                    line_size = len(line)
                    if current_size + line_size > config.code_chunk_size and current_chunk_lines:
                        # 保存当前块
                        chunk_text = '\n'.join(current_chunk_lines)
                        chunks.append({
                            "text": chunk_text,
                            "chunk_index": len(chunks),
                            "element_type": element_type,
                            "strategy": ChunkStrategy.ADAPTIVE.value,
                            "metadata": {
                                "original_size": len(chunk_text),
                                "line_count": len(current_chunk_lines),
                                "is_complete_code_block": False
                            }
                        })
                        current_chunk_lines = [line]
                        current_size = line_size
                    else:
                        current_chunk_lines.append(line)
                        current_size += line_size
                
                # 添加最后一个块
                if current_chunk_lines:
                    chunk_text = '\n'.join(current_chunk_lines)
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": len(chunks),
                        "element_type": element_type,
                        "strategy": ChunkStrategy.ADAPTIVE.value,
                        "metadata": {
                            "original_size": len(chunk_text),
                            "line_count": len(current_chunk_lines),
                            "is_complete_code_block": len(current_chunk_lines) == len(lines)  # 是否是完整的代码块
                        }
                    })
            else:
                # 保持小代码块完整
                chunks.append({
                    "text": text,
                    "chunk_index": 0,
                    "element_type": element_type,
                    "strategy": ChunkStrategy.PRESERVE_BLOCK.value,
                    "metadata": {
                        "original_size": len(text),
                        "is_complete_code_block": True
                    }
                })
        else:
            # 如果不需要保持完整，则按固定大小分块
            chunks.extend(self._fixed_size_chunk(text, element_type, config.code_chunk_size))
        
        return chunks
    
    def _fixed_size_chunk(self, text: str, element_type: str, chunk_size: int) -> List[Dict[str, Any]]:
        """按固定大小分块"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size]
            chunks.append({
                "text": chunk_text,
                "chunk_index": len(chunks),
                "element_type": element_type,
                "strategy": ChunkStrategy.FIXED_SIZE.value,
                "metadata": {
                    "original_size": len(chunk_text)
                }
            })
        return chunks


class TableChunker(AdaptiveChunker):
    """表格分块器"""
    
    def chunk(self, text: str, element_type: str, file_type: str, config: ChunkConfig = None) -> List[Dict[str, Any]]:
        """
        表格分块逻辑
        根据配置决定是保持完整、按行分割还是其他策略
        """
        if config is None:
            config = ChunkConfig()
        
        # 检测是否为Markdown表格（以|分隔的行）
        lines = text.split('\n')
        is_markdown_table = any(re.match(r'^\s*\|', line) for line in lines)
        
        if is_markdown_table:
            # 处理Markdown表格
            if config.table_chunk_strategy == "whole":
                # 保持整个表格完整
                return [{
                    "text": text,
                    "chunk_index": 0,
                    "element_type": element_type,
                    "strategy": ChunkStrategy.PRESERVE_BLOCK.value,
                    "metadata": {
                        "original_size": len(text),
                        "row_count": len([line for line in lines if line.strip()]),
                        "is_complete_table": True
                    }
                }]
            elif config.table_chunk_strategy == "row_split":
                # 按行分割表格
                rows = [line for line in lines if line.strip()]
                chunks = []
                
                for i in range(0, len(rows), config.table_max_rows_per_chunk):
                    chunk_rows = rows[i:i + config.table_max_rows_per_chunk]
                    chunk_text = '\n'.join(chunk_rows)
                    
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": len(chunks),
                        "element_type": element_type,
                        "strategy": ChunkStrategy.SEMANTIC_BOUNDARY.value,
                        "metadata": {
                            "original_size": len(chunk_text),
                            "row_count": len(chunk_rows),
                            "is_complete_table": False,
                            "row_range": [i, min(i + config.table_max_rows_per_chunk, len(rows))]
                        }
                    })
                
                return chunks
            else:
                # 默认策略：保持完整
                return [{
                    "text": text,
                    "chunk_index": 0,
                    "element_type": element_type,
                    "strategy": ChunkStrategy.PRESERVE_BLOCK.value,
                    "metadata": {
                        "original_size": len(text),
                        "row_count": len([line for line in lines if line.strip()]),
                        "is_complete_table": True
                    }
                }]
        else:
            # 对于非Markdown表格，按固定大小处理
            chunker = FixedSizeChunker()
            return chunker.chunk(text, element_type, file_type, config)


class ParagraphChunker(AdaptiveChunker):
    """段落分块器"""
    
    def chunk(self, text: str, element_type: str, file_type: str, config: ChunkConfig = None) -> List[Dict[str, Any]]:
        """
        段落分块逻辑
        按固定大小分块，但尽可能在句子或单词边界处分割
        """
        if config is None:
            config = ChunkConfig()
        
        chunks = []
        
        # 如果文本长度小于分块大小，则不拆分
        if len(text) <= config.paragraph_chunk_size:
            chunks.append({
                "text": text,
                "chunk_index": 0,
                "element_type": element_type,
                "strategy": ChunkStrategy.PRESERVE_BLOCK.value,
                "metadata": {
                    "original_size": len(text),
                    "sentence_count": len(self._split_into_sentences(text))
                }
            })
            return chunks
        
        # 按语义边界（如句子）分割
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        start_pos = 0
        
        for sentence in sentences:
            # 检查添加当前句子是否会超出分块大小
            if len(current_chunk) + len(sentence) <= config.paragraph_chunk_size:
                current_chunk += sentence
            else:
                # 如果当前块有足够的内容，保存它
                if current_chunk.strip():
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_index": len(chunks),
                        "element_type": element_type,
                        "strategy": ChunkStrategy.SEMANTIC_BOUNDARY.value,
                        "metadata": {
                            "original_size": len(current_chunk),
                            "sentence_count": len(self._split_into_sentences(current_chunk))
                        }
                    })
                
                # 如果单个句子就超过了分块大小，需要按字数切分
                if len(sentence) > config.paragraph_chunk_size:
                    # 将长句子按固定大小切分
                    for i in range(0, len(sentence), config.paragraph_chunk_size):
                        chunk_text = sentence[i:i + config.paragraph_chunk_size]
                        chunks.append({
                            "text": chunk_text,
                            "chunk_index": len(chunks),
                            "element_type": element_type,
                            "strategy": ChunkStrategy.FIXED_SIZE.value,
                            "metadata": {
                                "original_size": len(chunk_text),
                                "sentence_count": 0
                            }
                        })
                    current_chunk = ""
                else:
                    # 开始新块
                    current_chunk = sentence
        
        # 添加最后一个块
        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_index": len(chunks),
                "element_type": element_type,
                "strategy": ChunkStrategy.SEMANTIC_BOUNDARY.value,
                "metadata": {
                    "original_size": len(current_chunk),
                    "sentence_count": len(self._split_into_sentences(current_chunk))
                }
            })
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 使用正则表达式分割句子
        sentence_pattern = re.compile(r'([.!?。！？]+)(?=\s|$|[A-ZА-Я])')
        parts = sentence_pattern.split(text)
        
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            if i < len(parts):
                sentence = parts[i]
                if i + 1 < len(parts):
                    sentence += parts[i + 1]  # 添加标点符号
                sentences.append(sentence)
        
        # 如果最后一部分没有标点符号，也加入
        if len(parts) % 2 == 1:
            last_part = parts[-1]
            if last_part.strip() and sentences:
                sentences[-1] += last_part
            elif last_part.strip():
                sentences.append(last_part)
        
        return [s for s in sentences if s.strip()]


class FixedSizeChunker(AdaptiveChunker):
    """固定大小分块器"""
    
    def chunk(self, text: str, element_type: str, file_type: str, config: ChunkConfig = None) -> List[Dict[str, Any]]:
        """
        按固定大小分块，尽可能在单词边界处分割
        """
        if config is None:
            config = ChunkConfig()
        
        chunk_size = config.default_chunk_size
        
        # 按单词边界分割，而不是硬性截断
        chunks = []
        words = text.split()
        
        current_chunk_words = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size <= chunk_size:
                current_chunk_words.append(word)
                current_size += word_size
            else:
                # 当前块已满，保存它
                if current_chunk_words:
                    chunk_text = ' '.join(current_chunk_words)
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": len(chunks),
                        "element_type": element_type,
                        "strategy": ChunkStrategy.FIXED_SIZE.value,
                        "metadata": {
                            "original_size": len(chunk_text),
                            "word_count": len(current_chunk_words)
                        }
                    })
                
                # 开始新块
                current_chunk_words = [word]
                current_size = word_size
        
        # 添加最后一个块
        if current_chunk_words:
            chunk_text = ' '.join(current_chunk_words)
            chunks.append({
                "text": chunk_text,
                "chunk_index": len(chunks),
                "element_type": element_type,
                "strategy": ChunkStrategy.FIXED_SIZE.value,
                "metadata": {
                    "original_size": len(chunk_text),
                    "word_count": len(current_chunk_words)
                }
            })
        
        return chunks


class AdaptiveChunkerFactory:
    """自适应分块器工厂类"""
    
    @staticmethod
    def get_chunker(element_type: str) -> AdaptiveChunker:
        """
        根据元素类型获取相应的分块器
        
        Args:
            element_type: 元素类型
            
        Returns:
            对应的分块器实例
        """
        if element_type.lower() == "code_block":
            return CodeBlockChunker()
        elif element_type.lower() == "table":
            return TableChunker()
        elif element_type.lower() == "paragraph":
            return ParagraphChunker()
        else:
            return FixedSizeChunker()