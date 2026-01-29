"""
核心服务接口
提供文档处理和向量化存储的统一接口
"""
import os
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from uuid import uuid4

# 导入文档预处理器模块
from core.doc_preprocessor.format_router.format_router import FormatRouter
from core.doc_preprocessor.parsing_cluster.markdown_parser import MarkdownParser
from core.doc_preprocessor.parsing_cluster.plain_text_parser import PlainTextParser
from core.doc_preprocessor.parsing_cluster.image_parser import ImageParser
from core.doc_preprocessor.text_cleaner.basic_cleaner import BasicTextCleaner
from core.doc_preprocessor.chunking_engine.engine import SmartChunkingEngine
from core.doc_preprocessor.chunking_engine.adaptive_chunker.chunker import ChunkConfig

# 导入向量引擎模块
from core.vector_engine.batch_processor.processor import BatchVectorProcessor, BatchProcessorConfig
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy
from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.embedding_loader.loader import EmbeddingModelLoader

# 导入RAG引擎模块
from core.rag_engine.api.rag_service import RAGService, AskConfig
from core.rag_engine.orchestrator import RAGOrchestrator
from core.rag_engine.query_understanding.context_state import ConversationState
from core.rag_engine.llm_client.deepseek_client import DeepSeekClient
from core.vector_engine.embedding_loader.model_manager import EmbeddingModelManager


class CoreServiceInterface:
    """
    核心服务接口类
    提供文档上传、处理和向量化存储的统一入口
    """
    
    def __init__(self):
        # 初始化文档预处理器组件
        self.format_router = FormatRouter()
        self.basic_cleaner = BasicTextCleaner()
        self.chunk_config = ChunkConfig(default_chunk_size=500)
        self.chunking_engine = SmartChunkingEngine(config=self.chunk_config)
        
        # 初始化向量引擎组件
        try:
            # 创建向量引擎配置
            batch_config = BatchProcessorConfig()
            self.batch_processor = BatchVectorProcessor(config=batch_config)
        except FileNotFoundError as e:
            print(f"警告: 无法初始化批量处理器 - {e}")
            self.batch_processor = None
        
        # 初始化向量数据库代理
        try:
            db_config = VectorDBConfig()
            self.vector_db_proxy = VectorDBProxy(db_config)
        except Exception as e:
            print(f"警告: 无法初始化向量数据库代理 - {e}")
            self.vector_db_proxy = None
        
        # 初始化嵌入模型加载器
        try:
            self.embedding_loader = EmbeddingModelLoader()
        except FileNotFoundError as e:
            print(f"警告: 无法初始化嵌入模型加载器 - {e}")
            self.embedding_loader = None
        
        # 初始化RAG引擎组件
        try:
            # 初始化嵌入模型管理器（用于RAG服务）
            self.embedding_model_manager = EmbeddingModelManager()
            
            # 初始化LLM客户端（使用DeepSeek或其他）
            # 这里使用占位符，实际部署时应从配置或环境变量获取API密钥
            try:
                self.llm_client = DeepSeekClient(api_key=os.getenv("DEEPSEEK_API_KEY", "your-api-key-here"))
            except Exception as e:
                print(f"警告: 无法初始化LLM客户端 - {e}")
                self.llm_client = None
                
            # 初始化RAG服务
            if self.vector_db_proxy and self.embedding_model_manager and self.llm_client:
                self.rag_config = AskConfig()
                self.rag_service = RAGService(
                    db_proxy=self.vector_db_proxy,
                    embedding_model_manager=self.embedding_model_manager,
                    llm_client=self.llm_client,
                    cfg=self.rag_config
                )
            else:
                self.rag_service = None
        except Exception as e:
            print(f"警告: 无法初始化RAG服务 - {e}")
            self.rag_service = None
        
        # 注册解析器到格式路由器
        self._register_parsers()
    
    def _register_parsers(self):
        """注册解析器到格式路由器"""
        # 注册Markdown解析器
        self.format_router.register_parser(
            mime_types=['text/markdown', 'text/x-markdown'],
            parser_callable=lambda file_path, user_id, team_id, config: MarkdownParser().parse(file_path, user_id, team_id)
        )
        
        # 注册纯文本解析器
        self.format_router.register_parser(
            mime_types=['text/plain'],
            parser_callable=lambda file_path, user_id, team_id, config: PlainTextParser().parse(file_path, user_id, team_id)
        )
        
        # 注册图像解析器（用于OCR）
        self.format_router.register_parser(
            mime_types=['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'],
            parser_callable=lambda file_path, user_id, team_id, config: ImageParser().parse(file_path, user_id, team_id)
        )
    
    def upload_file(self, 
                   file_path: str, 
                   user_id: str, 
                   knowledge_base_id: str,
                   file_name: Optional[str] = None,
                   custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        文件上传接口
        
        Args:
            file_path: 上传文件的本地路径
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            file_name: 文件名（可选，如果不提供则从file_path提取）
            custom_metadata: 自定义元数据（可选）
            
        Returns:
            处理结果字典，包含文档ID和处理状态
        """
        try:
            # 如果没有提供文件名，则从路径中提取
            if not file_name:
                file_name = Path(file_path).name
            
            # 生成文档ID
            document_id = f"doc_{str(uuid4())[:8]}"
            
            print(f"开始处理文档: {file_name} (ID: {document_id})")
            
            # 1. 使用文档预处理器进行处理
            processed_result = self._process_document(
                file_path=file_path,
                document_id=document_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                file_name=file_name
            )
            
            # 2. 使用向量引擎进行批量处理和存储
            storage_result = self._store_vectors(
                chunks=processed_result['chunks'],
                document_id=document_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                custom_metadata=custom_metadata
            )
            
            # 3. 返回处理结果
            result = {
                "document_id": document_id,
                "file_name": file_name,
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "status": "success",
                "message": "文档处理和存储成功",
                "processed_elements_count": len(processed_result.get('elements', [])),
                "chunk_count": len(processed_result['chunks']),
                "storage_result": storage_result
            }
            
            print(f"文档处理完成: {file_name} (ID: {document_id})")
            return result
            
        except Exception as e:
            error_result = {
                "document_id": None,
                "file_name": file_name or "unknown",
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "status": "error",
                "message": f"处理失败: {str(e)}",
                "error_type": type(e).__name__
            }
            print(f"文档处理失败: {file_name or 'unknown'} - {str(e)}")
            return error_result
    
    def _process_document(self, 
                         file_path: str, 
                         document_id: str, 
                         user_id: str, 
                         knowledge_base_id: str,
                         file_name: str) -> Dict[str, Any]:
        """
        处理文档的核心逻辑
        按照以下流程处理：格式路由分发 -> 解析 -> 清洗 -> 分块
        
        Args:
            file_path: 文件路径
            document_id: 文档ID
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            file_name: 文件名
            
        Returns:
            包含处理结果的字典
        """
        print(f"  [1/4] 开始格式路由分发...")
        
        # 使用格式路由分发器识别文件类型并路由到适当解析器
        task_id = self.format_router.identify_and_route(
            file_path=file_path,
            user_id=user_id,
            team_id=knowledge_base_id,
        )
        
        # 等待任务完成并获取结果
        parse_result = self.format_router.get_task_result(task_id)
        
        if not parse_result:
            # 如果路由处理失败，尝试直接解析
            print(f"  [1/4] 格式路由未完成，尝试直接解析...")
            # 根据文件扩展名选择解析器
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in ['.md', '.markdown']:
                parser = MarkdownParser()
            elif file_ext in ['.txt', '.text']:
                parser = PlainTextParser()
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                parser = ImageParser()
            else:
                # 默认使用纯文本解析器
                parser = PlainTextParser()
            
            parse_result = parser.parse(file_path, user_id, knowledge_base_id)
        
        print(f"  [2/4] 解析完成，获得 {len(parse_result.get('elements', []))} 个元素")
        
        # 将解析结果中的字典转换为Element对象
        from core.doc_preprocessor.parsing_cluster.processor import Element
        elements = []
        for elem_dict in parse_result.get("elements", []):
            element = Element(
                raw_content=elem_dict["raw_content"],
                element_type=elem_dict["element_type"],
                element_index=elem_dict["element_index"],
                source_format=elem_dict["source_format"],
                format_metadata=elem_dict.get("format_metadata", {}),
                parser_confidence=elem_dict.get("parser_confidence", 1.0)
            )
            elements.append(element)
        
        print(f"  [3/4] 开始文本清洗...")
        # 文本清洗
        cleaned_elements = self.basic_cleaner.clean(elements)
        print(f"  [3/4] 清洗完成")
        
        print(f"  [4/4] 开始内容分块...")
        # 使用分块引擎进行分块
        chunk_result = self.chunking_engine.chunk_elements(
            elements=cleaned_elements,
            document_id=document_id,
            team_id=knowledge_base_id,
            user_id=user_id,
            file_name=file_name,
            file_type=Path(file_path).suffix.lower()[1:] or "unknown",  # 移除点号
            overlap_size=50
        )
        print(f"  [4/4] 分块完成，获得 {len(chunk_result.get('chunks', []))} 个文本块")
        
        return {
            "elements": elements,
            "cleaned_elements": cleaned_elements,
            "chunks": chunk_result.get('chunks', []),
            "parse_result": parse_result
        }
    
    def _store_vectors(self,
                      chunks: list,
                      document_id: str,
                      user_id: str,
                      knowledge_base_id: str,
                      custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        存储向量的核心逻辑
        将分块结果通过向量引擎进行批量处理并存储到向量数据库
        
        Args:
            chunks: 分块结果列表
            document_id: 文档ID
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            custom_metadata: 自定义元数据
            
        Returns:
            存储结果字典
        """
        print(f"  开始向量化和存储...")
        
        # 准备批量处理的数据
        batch_data = []
        for i, chunk in enumerate(chunks):
            # 构建每块的元数据
            chunk_metadata = {
                "document_id": document_id,
                "chunk_index": i,
                "element_type": chunk.get("element_type", "unknown"),
                "structure_path": chunk.get("structure_path", []),
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id
            }
            
            # 添加自定义元数据
            if custom_metadata:
                chunk_metadata.update(custom_metadata)
            
            batch_data.append({
                "text": chunk.get("text", ""),
                "metadata": chunk_metadata,
                "chunk_id": f"{document_id}_chunk_{i}"
            })
        
        # 检查向量引擎组件是否可用
        if self.batch_processor and self.vector_db_proxy:
            # 准备交付数据给批量处理器
            delivery_data = {
                "document_id": document_id,
                "user_id": user_id,
                "team_id": knowledge_base_id,
                "file_type": "document",  # 根据实际文件类型调整
                "chunks": []  # 将chunks格式化为批量处理器需要的格式
            }
            
            # 格式化chunks为批量处理器所需的格式
            for i, chunk in enumerate(chunks):
                chunk_data = {
                    "text": chunk.get("text", ""),
                    "chunk_index": chunk.get("chunk_index", i),
                    "element_type": chunk.get("element_type", "unknown"),
                    "structure_path": chunk.get("structure_path", []),
                    "metadata": chunk.get("metadata", {})
                }
                delivery_data["chunks"].append(chunk_data)
            
            # 使用批量处理器处理数据
            try:
                # 加载模型（这里假设使用默认模型）
                if not self.batch_processor._model_loaded:
                    self.batch_processor.load_model("all-MiniLM-L6-v2")  # 使用默认模型名称
                
                processed_result = self.batch_processor.process_batch(delivery_data)
                
                # 存储到向量数据库
                if processed_result.get("success", False):
                    store_result = processed_result
                else:
                    store_result = {"error": processed_result.get("message", "批量处理失败")}
                    
            except Exception as e:
                print(f"批量处理失败: {str(e)}")
                store_result = {"error": str(e)}
        else:
            # 如果向量引擎组件不可用，返回警告信息
            print("警告: 向量引擎组件不可用，仅完成文档预处理")
            store_result = {
                "warning": "向量引擎组件不可用，仅完成文档预处理",
                "processed_chunks": len(chunks),
                "status": "preprocessing_only"
            }
        
        result = {
            "stored_chunks_count": len(chunks),
            "database_store_result": store_result,
            "status": "success"
        }
        
        print(f"  向量化和存储完成，存储了 {len(chunks)} 个文本块")
        return result
    
    def ask_question(self,
                   question: str,
                   user_id: str,
                   knowledge_base_id: str,
                   model_alias: str = "default",
                   conversation_state: Optional[ConversationState] = None,
                   stream: bool = False,
                   top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        用户提问接口
        
        Args:
            question: 用户提出的问题
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            model_alias: 使用的模型别名
            conversation_state: 对话状态（用于多轮对话）
            stream: 是否使用流式输出
            top_k: 检索的top-k数量
            
        Returns:
            包含答案和相关信息的字典
        """
        try:
            # 检查RAG服务是否可用
            if not self.rag_service:
                return {
                    "status": "error",
                    "message": "RAG服务不可用",
                    "answer": "抱歉，问答服务当前不可用。",
                    "citations": [],
                    "debug": {}
                }
            
            # 设置对话状态
            if conversation_state is None:
                conversation_state = ConversationState()
                conversation_state.user_context.knowledge_base_id = knowledge_base_id
                conversation_state.user_context.user_id = user_id
            
            print(f"开始处理用户提问: {question[:50]}...")
            
            # 调用RAG服务进行问答
            result = self.rag_service.ask(
                question=question,
                model_alias=model_alias,
                conversation_state=conversation_state,
                stream=stream,
                top_k=top_k
            )
            
            # 如果是流式响应，需要特别处理
            if stream and "stream" in result:
                # 将流式响应转换为完整响应（在实际应用中，这里可能需要特殊处理）
                answer_parts = []
                for chunk in result["stream"]:
                    answer_parts.append(chunk)
                result["answer"] = "".join(answer_parts)
                del result["stream"]
            
            result["status"] = "success"
            result["question"] = question
            result["user_id"] = user_id
            result["knowledge_base_id"] = knowledge_base_id
            
            print(f"用户提问处理完成")
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "message": f"提问处理失败: {str(e)}",
                "answer": "抱歉，处理您的问题时出现错误。",
                "citations": [],
                "debug": {"error_type": type(e).__name__}
            }
            print(f"用户提问处理失败: {str(e)}")
            return error_result


# 全局接口实例
core_service = CoreServiceInterface()


def upload_file_interface(file_path: str, 
                        user_id: str, 
                        knowledge_base_id: str,
                        file_name: Optional[str] = None,
                        custom_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    文件上传接口函数
    
    Args:
        file_path: 上传文件的本地路径
        user_id: 用户ID
        knowledge_base_id: 知识库ID
        file_name: 文件名（可选）
        custom_metadata: 自定义元数据（可选）
        
    Returns:
        处理结果字典
    """
    return core_service.upload_file(
        file_path=file_path,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        file_name=file_name,
        custom_metadata=custom_metadata
    )


def ask_question_interface(question: str,
                         user_id: str,
                         knowledge_base_id: str,
                         model_alias: str = "default",
                         stream: bool = False,
                         top_k: Optional[int] = None) -> Dict[str, Any]:
    """
    用户提问接口函数
    
    Args:
        question: 用户提出的问题
        user_id: 用户ID
        knowledge_base_id: 知识库ID
        model_alias: 使用的模型别名
        stream: 是否使用流式输出
        top_k: 检索的top-k数量
        
    Returns:
        包含答案和相关信息的字典
    """
    return core_service.ask_question(
        question=question,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        model_alias=model_alias,
        stream=stream,
        top_k=top_k
    )


# 示例使用
if __name__ == "__main__":
    # 示例调用
    result = upload_file_interface(
        file_path="./test_sample.md",
        user_id="user_123",
        knowledge_base_id="kb_456",
        file_name="test_sample.md",
        custom_metadata={"category": "documentation", "tags": ["test", "example"]}
    )
    print(result)