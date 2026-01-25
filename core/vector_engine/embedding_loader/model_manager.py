"""
嵌入模型管理器
提供高级接口来管理多个嵌入模型
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import torch

from .loader import EmbeddingModelLoader

logger = logging.getLogger(__name__)


class EmbeddingModelManager:
    """嵌入模型管理器类"""
    
    def __init__(self, model_dir: str = "../../../model"):
        """
        初始化模型管理器
        
        Args:
            model_dir: 模型目录路径
        """
        self.loader = EmbeddingModelLoader(model_dir)
        self.active_models: Dict[str, Any] = {}  # 存储当前活跃的模型引用（别名 -> 模型对象）
        self.model_alias_mapping: Dict[str, str] = {}  # 存储别名到原始模型名的映射（别名 -> 原始模型名）
    
    def list_available_models(self) -> List[str]:
        """
        列出所有可用的模型
        
        Returns:
            可用模型名称列表
        """
        return self.loader.list_available_models()
    
    def load_model(self, model_name: str, alias: Optional[str] = None, device: str = None, **kwargs) -> bool:
        """
        加载模型到内存
        
        Args:
            model_name: 原始模型名称
            alias: 模型别名，如果不提供则使用原名
            device: 设备类型，如果为None则自动选择（优先GPU）
            **kwargs: 其他参数
            
        Returns:
            是否成功加载
        """
        # 如果没有指定设备，则自动选择
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"自动选择设备: {device}")
        
        # 使用别名或原始名称作为键
        model_key = alias if alias else model_name
        
        if model_key in self.active_models:
            logger.warning(f"模型 {model_key} 已经在内存中")
            return False
        
        model = self.loader.load_model(model_name, device, **kwargs)
        if model is not None:
            self.active_models[model_key] = model
            # 记录别名到原始模型名的映射
            self.model_alias_mapping[model_key] = model_name
            logger.info(f"模型 {model_key} 已加载到内存，设备: {device}")
            return True
        else:
            logger.error(f"加载模型 {model_key} 失败")
            return False
    
    def unload_model(self, alias: str) -> bool:
        """
        从内存中卸载模型
        
        Args:
            alias: 模型别名
            
        Returns:
            是否成功卸载
        """
        if alias not in self.active_models:
            logger.warning(f"模型 {alias} 不在内存中，无法卸载")
            return False
        
        # 从活跃模型中移除
        del self.active_models[alias]
        
        # 从映射中移除
        if alias in self.model_alias_mapping:
            original_model_name = self.model_alias_mapping[alias]
            del self.model_alias_mapping[alias]
            # 同时尝试从加载器中卸载原始模型
            self.loader.unload_model(original_model_name)
        
        logger.info(f"模型 {alias} 已从内存中卸载")
        return True
    
    def get_model(self, alias: str) -> Optional[Any]:
        """
        获取已加载的模型
        
        Args:
            alias: 模型别名
            
        Returns:
            模型对象，如果不存在则返回None
        """
        return self.active_models.get(alias)
    
    def encode(self, alias: str, sentences: List[str], **kwargs) -> Optional[Any]:
        """
        使用指定模型对句子进行编码
        
        Args:
            alias: 模型别名
            sentences: 要编码的句子列表
            **kwargs: 编码参数
            
        Returns:
            编码结果
        """
        model = self.get_model(alias)
        if model is None:
            logger.error(f"模型 {alias} 未加载")
            return None
        
        try:
            embeddings = model.encode(sentences, **kwargs)
            return embeddings
        except Exception as e:
            logger.error(f"编码过程中发生错误: {str(e)}")
            return None
    
    def get_loaded_models_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取已加载模型的信息
        
        Returns:
            模型信息字典
        """
        info = {}
        for alias, model in self.active_models.items():
            info[alias] = {
                'model_name': getattr(model, 'model_card_data', {}).get('base_model_name_or_path', 'Unknown'),
                'max_seq_length': getattr(model, 'max_seq_length', 'Unknown'),
                'device': getattr(model, '_target_device', 'Unknown')
            }
        return info
    
    def get_memory_usage(self) -> Dict[str, int]:
        """
        获取模型内存使用情况（近似值）
        
        Returns:
            内存使用情况字典
        """
        usage = {}
        for alias, model in self.active_models.items():
            # 这里只是一个估算，实际内存使用会更复杂
            try:
                # 计算模型参数数量
                param_count = sum(p.numel() for p in model._modules.parameters()) if hasattr(model._modules, 'parameters') else 0
                # 估算内存使用（假设每个参数4字节 float32）
                estimated_mb = (param_count * 4) / (1024 * 1024) if param_count > 0 else 0
                usage[alias] = round(estimated_mb, 2)
            except:
                usage[alias] = 0  # 无法计算时返回0
        
        return usage
    
    def unload_all_models(self) -> bool:
        """
        卸载所有已加载的模型
        
        Returns:
            是否成功卸载所有模型
        """
        aliases_to_unload = list(self.active_models.keys())
        success = True
        
        for alias in aliases_to_unload:
            if not self.unload_model(alias):
                success = False
        
        logger.info("已尝试卸载所有模型")
        return success
    
    def reload_model(self, model_name: str, alias: Optional[str] = None, device: str = None, **kwargs) -> bool:
        """
        重新加载模型（先卸载再加载）
        
        Args:
            model_name: 模型名称
            alias: 模型别名
            device: 设备类型，如果为None则自动选择（优先GPU）
            **kwargs: 其他参数
            
        Returns:
            是否成功重新加载
        """
        # 如果没有指定设备，则自动选择
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"自动选择设备: {device}")
        
        model_key = alias if alias else model_name
        
        # 先卸载现有模型
        if model_key in self.active_models:
            self.unload_model(model_key)
        
        # 再加载新模型
        return self.load_model(model_name, alias, device, **kwargs)