"""
嵌入模型加载器工具类
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import json
import psutil
import GPUtil


def get_disk_usage(path: str) -> Dict[str, float]:
    """
    获取磁盘使用情况
    
    Args:
        path: 路径
        
    Returns:
        磁盘使用情况字典
    """
    usage = shutil.disk_usage(path)
    total = usage.total / (1024 ** 3)  # GB
    free = usage.free / (1024 ** 3)    # GB
    used = usage.used / (1024 ** 3)    # GB
    
    return {
        'total_gb': round(total, 2),
        'free_gb': round(free, 2),
        'used_gb': round(used, 2),
        'usage_percent': round((used / total) * 100, 2)
    }


def get_memory_usage() -> Dict[str, float]:
    """
    获取系统内存使用情况
    
    Returns:
        内存使用情况字典
    """
    memory = psutil.virtual_memory()
    return {
        'total_gb': round(memory.total / (1024 ** 3), 2),
        'available_gb': round(memory.available / (1024 ** 3), 2),
        'used_gb': round(memory.used / (1024 ** 3), 2),
        'usage_percent': memory.percent
    }


def get_gpu_info() -> List[Dict[str, any]]:
    """
    获取GPU信息
    
    Returns:
        GPU信息列表
    """
    gpus = GPUtil.getGPUs()
    gpu_info = []
    
    for gpu in gpus:
        gpu_info.append({
            'id': gpu.id,
            'name': gpu.name,
            'memory_total': gpu.memoryTotal,
            'memory_used': gpu.memoryUsed,
            'memory_free': gpu.memoryFree,
            'driver': gpu.driver,
            'gpu_util': gpu.load * 100,
            'memory_util': gpu.memoryUtil * 100
        })
    
    return gpu_info


def estimate_model_size(model_path: str) -> float:
    """
    估算模型大小
    
    Args:
        model_path: 模型路径
        
    Returns:
        模型大小（MB）
    """
    total_size = 0
    model_dir = Path(model_path)
    
    if model_dir.exists():
        for file_path in model_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    
    return round(total_size / (1024 * 1024), 2)  # 返回MB


def validate_model_directory(model_path: str) -> bool:
    """
    验证模型目录是否有效
    
    Args:
        model_path: 模型路径
        
    Returns:
        是否有效
    """
    model_dir = Path(model_path)
    
    if not model_dir.exists() or not model_dir.is_dir():
        return False
    
    # 检查必需的模型文件
    required_files = [
        'config.json',
        'tokenizer_config.json'
    ]
    
    has_required_files = any((model_dir / f).exists() for f in required_files)
    
    # 检查模型权重文件
    weight_files = [
        'pytorch_model.bin',
        'model.safetensors',
        'tf_model.h5'
    ]
    
    has_weight_files = any((model_dir / f).exists() for f in weight_files)
    
    return has_required_files and has_weight_files


def get_available_devices() -> List[str]:
    """
    获取可用的设备列表
    
    Returns:
        设备列表
    """
    devices = ["cpu"]
    
    # 检查CUDA
    try:
        import torch
        if torch.cuda.is_available():
            devices.append("cuda")
            # 添加具体的GPU设备
            for i in range(torch.cuda.device_count()):
                devices.append(f"cuda:{i}")
    except ImportError:
        pass
    
    # 检查MPS (Apple Silicon)
    try:
        import torch
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            devices.append("mps")
    except ImportError:
        pass
    
    return devices


def format_bytes(bytes_value: int) -> str:
    """
    格式化字节数为人类可读格式
    
    Args:
        bytes_value: 字节数
        
    Returns:
        格式化后的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def save_model_metadata(model_name: str, model_path: str, metadata: Dict) -> bool:
    """
    保存模型元数据
    
    Args:
        model_name: 模型名称
        model_path: 模型路径
        metadata: 元数据字典
        
    Returns:
        是否保存成功
    """
    try:
        metadata_path = Path(model_path) / f"{model_name}_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_model_metadata(model_name: str, model_path: str) -> Optional[Dict]:
    """
    加载模型元数据
    
    Args:
        model_name: 模型名称
        model_path: 模型路径
        
    Returns:
        元数据字典，如果不存在则返回None
    """
    try:
        metadata_path = Path(model_path) / f"{model_name}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception:
        return None