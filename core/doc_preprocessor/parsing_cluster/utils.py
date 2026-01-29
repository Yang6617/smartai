"""
文档预处理器工具函数
提供通用的辅助功能
"""

import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any


def generate_document_id(file_path: str, user_id: str, knowledge_base_id: str) -> str:
    """
    生成文档ID
    
    Args:
        file_path: 文件路径
        user_id: 用户ID
        knowledge_base_id: 知识库ID
        
    Returns:
        生成的文档ID
    """
    file_content = Path(file_path).read_bytes()
    content_hash = hashlib.md5(file_content).hexdigest()[:8]
    return f"doc_{user_id}_{knowledge_base_id}_{content_hash}_{str(uuid.uuid4())[:8]}"


def normalize_file_path(file_path: str) -> str:
    """
    规范化文件路径
    
    Args:
        file_path: 原始文件路径
        
    Returns:
        规范化后的文件路径
    """
    return str(Path(file_path).resolve())


def validate_file_size(file_path: str, max_size: int) -> bool:
    """
    验证文件大小是否符合要求
    
    Args:
        file_path: 文件路径
        max_size: 最大大小（字节）
        
    Returns:
        文件大小是否符合要求
    """
    file_size = Path(file_path).stat().st_size
    return file_size <= max_size


def extract_file_extension(file_path: str) -> str:
    """
    提取文件扩展名
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件扩展名（包含点号）
    """
    return Path(file_path).suffix.lower()


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除路径分隔符等不安全字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()