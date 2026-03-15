"""
Configuration module for vector database connections.
"""

import sys
import os
# 添加项目根目录到系统路径，以便导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class VectorDBConfig:
    """
    Configuration class for vector database connections.
    """
    # Database type (chromadb, pinecone, weaviate, etc.)
    db_type: str = "chromadb"
    
    # Connection parameters - default to empty values to favor persistent mode
    host: str = ""  # Empty string defaults to persistent mode
    port: int = 0   # Zero defaults to persistent mode
    path: Optional[str] = None  # If None, use default path: ./chroma_data relative to project root
    api_key: Optional[str] = None
    ssl: bool = False
    
    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600  # Recycle connections after 1 hour
    
    # Additional options for different vector DBs
    additional_options: dict = None
    
    def __post_init__(self):
        if self.additional_options is None:
            self.additional_options = {}
        
        # If path is None, use default path relative to project root
        if self.path is None:
            # Try to find project root (ai_model_service directory)
            current_file = Path(__file__).resolve()
            # Go up from vector_db_proxy -> vector_engine -> core -> project root
            project_root = current_file.parent.parent.parent.parent
            self.path = str(project_root / "chroma_data")