"""
Batch processor for converting text chunks to vectors and storing them in the vector database.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# 为了支持不同的导入方式，尝试多种导入方法
try:
    # 作为包的一部分导入
    from .config import BatchProcessorConfig
    from ..embedding_loader import EmbeddingModelManager
    from ..vector_db_proxy.proxy import VectorDBProxy
    from ..vector_db_proxy.config import VectorDBConfig
except ImportError:
    # 直接运行时的导入
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).parent.parent.parent)
    sys.path.insert(0, project_root)
    
    from core.vector_engine.batch_processor.config import BatchProcessorConfig
    from core.vector_engine.embedding_loader import EmbeddingModelManager
    from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy
    from core.vector_engine.vector_db_proxy.config import VectorDBConfig


class BatchVectorProcessor:
    """
    批量向量化处理器
    负责将文本块列表转换为向量并存储到向量数据库中
    """
    
    def __init__(self, config: BatchProcessorConfig):
        """
        初始化批量向量化处理器
        
        Args:
            config: 批量处理器配置
        """
        self.config = config
        
        # 初始化嵌入模型管理器
        self.model_manager = EmbeddingModelManager(config.model_path)
        
        # 初始化向量数据库代理
        db_config = VectorDBConfig(
            db_type=config.db_type,
            path=config.db_path,
            host=config.db_host,
            port=config.db_port
        )
        self.db_proxy = VectorDBProxy(db_config)
        
        # 模型加载状态
        self._model_loaded = False
        self._loaded_model_alias = None
        
    def load_model(self, model_name: str, alias: Optional[str] = None, device: Optional[str] = None) -> bool:
        """
        加载嵌入模型
        
        Args:
            model_name: 模型名称
            alias: 模型别名
            device: 设备类型，如果为None则自动选择
            
        Returns:
            是否成功加载模型
        """
        success = self.model_manager.load_model(model_name, alias, device)
        if success:
            self._model_loaded = True
            self._loaded_model_alias = alias or model_name
        return success
    
    def unload_model(self, model_alias: Optional[str] = None) -> bool:
        """
        卸载嵌入模型
        
        Args:
            model_alias: 模型别名，如果不提供则使用当前加载的模型
        
        Returns:
            是否成功卸载模型
        """
        alias = model_alias or self._loaded_model_alias
        if alias:
            success = self.model_manager.unload_model(alias)
            if success and alias == self._loaded_model_alias:
                self._model_loaded = False
                self._loaded_model_alias = None
            return success
        return False
    
    def _prepare_metadata(self, chunk: Dict[str, Any], delivery_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备元数据
        
        Args:
            chunk: 文本块数据
            delivery_data: 交付数据
            
        Returns:
            元数据字典
        """
        # 构建结构化路径字符串
        structure_path_str = ""
        if "structure_path" in chunk and chunk["structure_path"]:
            structure_path_str = " > ".join(chunk["structure_path"])
        
        metadata = {
            "document_id": delivery_data.get("document_id", ""),
            "chunk_index": chunk.get("chunk_index", 0),
            "source_type": delivery_data.get("file_type", ""),
            "source_info": structure_path_str,
            "knowledge_base_id": delivery_data.get("team_id", ""),
            "uploader_id": delivery_data.get("user_id", ""),
            "version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        
        # 从chunk的metadata或format_metadata中提取bbox信息（用于图片等有位置信息的文档）
        bbox = None
        if "metadata" in chunk and chunk["metadata"] and isinstance(chunk["metadata"], dict):
            bbox = chunk["metadata"].get("bbox")
        if not bbox and "format_metadata" in chunk and chunk["format_metadata"] and isinstance(chunk["format_metadata"], dict):
            bbox = chunk["format_metadata"].get("bbox")
        
        if bbox and isinstance(bbox, list) and len(bbox) >= 4:
            # ChromaDB不支持列表作为metadata值，将其转换为字符串
            metadata["bbox"] = ",".join(str(x) for x in bbox)
        
        return metadata
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """
        生成文本块的唯一ID
        
        Args:
            document_id: 文档ID
            chunk_index: 文本块索引
            
        Returns:
            唯一ID
        """
        return f"{document_id}_chunk_{chunk_index}_{str(uuid.uuid4())[:8]}"
    
    def process_batch(self, delivery_data: Dict[str, Any], model_alias: Optional[str] = None) -> Dict[str, Any]:
        """
        处理批量文本块数据
        
        Args:
            delivery_data: 交付数据，包含文档信息和文本块列表
            model_alias: 模型别名，如果不提供则使用当前加载的模型
            
        Returns:
            处理结果
        """
        if not self._model_loaded:
            raise RuntimeError("No model loaded. Please load a model first.")
        
        model_alias = model_alias or self._loaded_model_alias
        if not model_alias:
            raise ValueError("No model alias provided and no model currently loaded.")
        
        # 连接到数据库
        if not self.db_proxy.connect():
            raise RuntimeError("Failed to connect to vector database.")
        
        try:
            # 获取文本块
            chunks = delivery_data.get("chunks", [])
            if not chunks:
                return {
                    "success": True,
                    "message": "No chunks to process",
                    "processed_count": 0
                }
            
            # 提取文本内容用于编码
            texts = [chunk["text"] for chunk in chunks if "text" in chunk]
            if not texts:
                return {
                    "success": True,
                    "message": "No text content to process",
                    "processed_count": 0
                }
            
            # 使用模型进行向量化
            embeddings = self.model_manager.encode(model_alias, texts)
            
            # 准备向量数据库所需的数据
            ids = []
            metadatas = []
            documents = []
            
            for i, chunk in enumerate(chunks):
                if "text" in chunk:
                    ids.append(self._generate_chunk_id(delivery_data["document_id"], chunk.get("chunk_index", i)))
                    metadatas.append(self._prepare_metadata(chunk, delivery_data))
                    documents.append(chunk["text"])
            
            # 将向量添加到数据库
            collection_name = f"kb_{delivery_data.get('team_id', 'default')}"
            # print(f"[DEBUG] Batch Processor - Storing in collection: {collection_name}")
            
            # 确保集合存在
            self.db_proxy.create_collection(collection_name)
            
            success = self.db_proxy.add_vectors(
                collection_name=collection_name,
                vectors=embeddings,
                ids=ids,
                metadatas=metadatas,
                documents=documents
            )
            
            if success:
                # 确保数据持久化 - 等待一点时间让数据库完成写入
                time.sleep(0.5)  # 增加等待时间
                
                # 验证数据是否可以被查询到（在当前连接上下文中）
                try:
                    count_in_current_connection = self.db_proxy.get_vector_count(collection_name)
                    # print(f"[DEBUG] Batch Processor - Count after add in current connection: {count_in_current_connection}")
                    
                    # 再等待一点时间确保数据被充分处理
                    time.sleep(0.3)
                    
                except Exception as e:
                    print(f"[DEBUG] Could not verify count in current connection: {e}")
                
                result = {
                    "success": True,
                    "message": f"Successfully processed {len(texts)} chunks",
                    "processed_count": len(texts),
                    "collection_name": collection_name,
                    "ids": ids
                }
            else:
                result = {
                    "success": False,
                    "message": "Failed to add vectors to database",
                    "processed_count": 0
                }
                
            # 在返回结果前尝试持久化数据
            try:
                adapter = self.db_proxy.current_adapter
                if hasattr(adapter, 'client') and adapter.client:
                    if hasattr(adapter.client, 'persist'):
                        # print("[DEBUG] Calling client.persist() in batch processor")
                        adapter.client.persist()
                        time.sleep(0.3)  # 增加等待时间
                    else:
                        # 如果没有 persist 方法，等待更长时间让自动持久化完成
                        # print("[DEBUG] No persist method, waiting for auto-persistence...")
                        time.sleep(1.0)
            except Exception as e:
                # print(f"[DEBUG] Persist operation failed: {e}")
                # 即使失败也等待一段时间
                time.sleep(0.5)
            
            return result
                
        finally:
            # 不在此处断开数据库连接，让调用者控制连接生命周期
            pass
    
    def batch_process_multiple_documents(self, documents_data: List[Dict[str, Any]], 
                                       model_alias: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        批量处理多个文档
        
        Args:
            documents_data: 文档数据列表
            model_alias: 模型别名
            
        Returns:
            处理结果列表
        """
        results = []
        for doc_data in documents_data:
            try:
                result = self.process_batch(doc_data, model_alias)
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "message": f"Error processing document {doc_data.get('document_id', 'unknown')}: {str(e)}",
                    "processed_count": 0
                })
        
        return results