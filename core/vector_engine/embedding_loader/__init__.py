"""
Embedding Model Loader Module
动态加载和卸载预训练嵌入模型
"""

from .model_manager import EmbeddingModelManager
from .loader import load_embedding_model, unload_embedding_model

__all__ = [
    'EmbeddingModelManager',
    'load_embedding_model',
    'unload_embedding_model'
]