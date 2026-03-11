"""
嵌入模型加载器
负责动态加载和卸载预训练嵌入模型
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("警告: 未安装sentence-transformers库，请运行 pip install sentence-transformers")
    SentenceTransformer = None

logger = logging.getLogger(__name__)

class EmbeddingModelLoader:
    """嵌入模型加载器类"""
    
    def __init__(self, model_dir: str = "model"):
        """
        初始化模型加载器
        
        Args:
            model_dir: 模型目录路径，默认为"model"（相对于当前工作目录）
        """
        self.model_dir = Path(model_dir).resolve()
        self.loaded_models: Dict[str, Any] = {}
        
        # 确保模型目录存在，如果不存在则记录警告但不抛出异常
        if not self.model_dir.exists():
            # 尝试使用当前工作目录下的model目录
            alt_model_dir = Path.cwd() / "model"
            if alt_model_dir.exists():
                self.model_dir = alt_model_dir
                print(f"使用备用模型目录: {self.model_dir}")
            else:
                # 最后尝试使用项目根目录下的model目录
                project_root = Path(__file__).parent.parent.parent
                alt_model_dir = Path(project_root) / "model"
                if alt_model_dir.exists():
                    self.model_dir = alt_model_dir
                    print(f"使用备用模型目录: {self.model_dir}")
                else:
                    print(f"备用模型目录也不存在: {alt_model_dir}")
    
    def list_available_models(self) -> list:
        """
        列出可用的模型
        
        Returns:
            可用模型名称列表
        """
        if not self.model_dir.exists():
            return []
        
        models = []
        for item in self.model_dir.iterdir():
            if item.is_dir():
                # 检查是否为有效的模型目录（包含必要的模型文件）
                if self._is_valid_model_dir(item):
                    models.append(item.name)
        
        return models
    
    def _is_valid_model_dir(self, model_path: Path) -> bool:
        """
        检查是否为有效的模型目录
        
        Args:
            model_path: 模型目录路径
            
        Returns:
            是否为有效模型目录
        """
        # 检查是否存在模型配置文件或其他关键文件
        required_files = ['config.json', 'pytorch_model.bin', 'tokenizer_config.json']
        
        for required_file in required_files:
            if (model_path / required_file).exists():
                return True
        
        # 如果没有找到标准的模型文件，检查是否有其他常见的模型文件
        model_files = ['model.safetensors', 'sentence_bert_config.json']
        for model_file in model_files:
            if (model_path / model_file).exists():
                return True
        
        return False
    
    def load_model(self, model_name: str, device: str = "cpu", **kwargs) -> Optional[Any]:
        """
        加载指定的嵌入模型
        
        Args:
            model_name: 模型名称
            device: 设备类型，如 "cpu", "cuda", "mps" 等
            **kwargs: 其他参数传递给SentenceTransformer
            
        Returns:
            加载的模型对象，如果失败则返回None
        """
        if SentenceTransformer is None:
            logger.error("无法加载模型：未安装sentence-transformers库")
            return None
        
        model_path = self.model_dir / model_name
        
        if not model_path.exists():
            logger.error(f"模型目录不存在: {model_path}")
            return None
        
        if not self._is_valid_model_dir(model_path):
            logger.error(f"无效的模型目录: {model_path}")
            return None
        
        try:
            # 尝试加载模型
            model = SentenceTransformer(
                str(model_path),
                device=device,
                **kwargs
            )
            
            # 将模型添加到已加载字典
            self.loaded_models[model_name] = model
            logger.info(f"成功加载模型: {model_name} 到设备: {device}")
            
            return model
            
        except Exception as e:
            logger.error(f"加载模型 {model_name} 时发生错误: {str(e)}")
            return None
    
    def unload_model(self, model_name: str) -> bool:
        """
        卸载指定的嵌入模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            是否成功卸载
        """
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            logger.info(f"成功卸载模型: {model_name}")
            return True
        else:
            logger.warning(f"模型 {model_name} 未被加载，无需卸载")
            return False
    
    def get_loaded_models(self) -> Dict[str, Any]:
        """
        获取当前已加载的模型列表
        
        Returns:
            已加载模型字典
        """
        return self.loaded_models.copy()
    
    def is_model_loaded(self, model_name: str) -> bool:
        """
        检查模型是否已加载
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型是否已加载
        """
        return model_name in self.loaded_models


# 全局模型加载器实例
_global_loader = None


def get_global_loader() -> EmbeddingModelLoader:
    """获取全局模型加载器实例"""
    global _global_loader
    if _global_loader is None:
        _global_loader = EmbeddingModelLoader()
    return _global_loader


def load_embedding_model(model_name: str, device: str = "cpu", **kwargs) -> Optional[Any]:
    """
    加载嵌入模型的便捷函数
    
    Args:
        model_name: 模型名称
        device: 设备类型
        **kwargs: 其他参数
        
    Returns:
        加载的模型对象
    """
    loader = get_global_loader()
    return loader.load_model(model_name, device, **kwargs)


def unload_embedding_model(model_name: str) -> bool:
    """
    卸载嵌入模型的便捷函数
    
    Args:
        model_name: 模型名称
        
    Returns:
        是否成功卸载
    """
    loader = get_global_loader()
    return loader.unload_model(model_name)