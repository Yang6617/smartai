"""
Configuration for the batch vector processor.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BatchProcessorConfig:
    """
    批量处理器配置
    """
    model_path: str = "../../model"  # 模型路径
    db_type: str = "chromadb"        # 数据库类型
    db_path: str = "../../data/chroma_persistent_data"  # 数据库路径
    db_host: str = ""                # 数据库主机
    db_port: int = 0                 # 数据库端口
    default_model: str = "bge-m3"    # 默认模型名称
    default_collection_prefix: str = "kb_"  # 默认集合前缀
    
    def __post_init__(self):
        """验证配置参数"""
        if not self.model_path:
            raise ValueError("Model path cannot be empty")
        if not self.db_type:
            raise ValueError("Database type cannot be empty")