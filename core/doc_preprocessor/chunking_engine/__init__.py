"""
智能分块引擎模块
将长文本分割为适合向量化的片段
"""
from .engine import SmartChunkingEngine
from .chunk import Chunk, format_chunks_for_output
from .adaptive_chunker.chunker import ChunkConfig

__all__ = [
    'SmartChunkingEngine',
    'Chunk',
    'format_chunks_for_output',
    'ChunkConfig'
]