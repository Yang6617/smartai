"""
嵌入模型加载器配置
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class EmbeddingModelConfig:
    """嵌入模型配置类"""
    
    model_name: str
    model_path: str = "../../model"
    device: str = "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = True
    max_seq_length: Optional[int] = None
    trust_remote_code: bool = False
    cache_folder: Optional[str] = None
    use_auth_token: Optional[bool] = None
    revision: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'model_name': self.model_name,
            'model_path': self.model_path,
            'device': self.device,
            'batch_size': self.batch_size,
            'normalize_embeddings': self.normalize_embeddings,
            'max_seq_length': self.max_seq_length,
            'trust_remote_code': self.trust_remote_code,
            'cache_folder': self.cache_folder,
            'use_auth_token': self.use_auth_token,
            'revision': self.revision
        }


# 预设模型配置
PRESET_MODELS = {
    "bge-m3": EmbeddingModelConfig(
        model_name="bge-m3",
        model_path="../../model/bge-m3",
        device="cpu",
        batch_size=16,
        normalize_embeddings=True,
        max_seq_length=8192
    ),
    # 可以在这里添加更多预设模型配置
}


def get_model_config(model_name: str) -> Optional[EmbeddingModelConfig]:
    """获取模型配置"""
    if model_name in PRESET_MODELS:
        return PRESET_MODELS[model_name]
    return None