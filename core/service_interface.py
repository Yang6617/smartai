"""
核心服务接口
提供文档处理和向量化存储的统一接口
"""
import os
import tempfile
from typing import Dict, Any, Optional, Union
from pathlib import Path
from uuid import uuid4

# 导入dotenv以支持从.env文件加载环境变量
try:
    from dotenv import load_dotenv
    # 加载项目根目录下的.env文件
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    
    # 也检查core目录下的.env文件
    core_env_file = Path(__file__).parent / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"已加载环境变量文件: {env_file}")
    elif core_env_file.exists():
        load_dotenv(core_env_file)
        print(f"已加载环境变量文件: {core_env_file}")
    else:
        print(f"未找到环境变量文件: {env_file} 或 {core_env_file}")
except ImportError:
    print("警告: python-dotenv未安装，无法从.env文件加载环境变量")

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
        
        # 初始化向量数据库代理（先初始化数据库代理）
        try:
            db_config = VectorDBConfig()
            self.vector_db_proxy = VectorDBProxy(db_config)
        except Exception as e:
            print(f"警告: 无法初始化向量数据库代理 - {e}")
            self.vector_db_proxy = None
        
        # 初始化向量引擎组件
        try:
            # 创建向量引擎配置，指定正确的模型路径
            from pathlib import Path
            model_dir = str(Path(__file__).parent.parent / "model")
            batch_config = BatchProcessorConfig(model_path=model_dir)
            self.batch_processor = BatchVectorProcessor(config=batch_config)
            
            # 让批量处理器使用与服务接口相同的数据库代理，确保数据一致性
            # 注意：我们会在_batch_vectors方法中动态替换，而不是在这里固定替换
        except FileNotFoundError as e:
            print(f"警告: 无法初始化批量处理器 - {e}")
            self.batch_processor = None
        
        # 初始化嵌入模型加载器
        try:
            self.embedding_loader = EmbeddingModelLoader()
        except FileNotFoundError as e:
            print(f"警告: 无法初始化嵌入模型加载器 - {e}")
            self.embedding_loader = None
        
        # 初始化RAG引擎组件
        try:
            # 初始化嵌入模型管理器（用于RAG服务）
            # 指定正确的模型目录路径 - 使用项目根目录下的model文件夹
            from pathlib import Path
            # 优先使用相对于当前工作目录的model目录（备用模型目录）
            model_dir = str(Path.cwd() / "model")
            
            # 如果当前工作目录下不存在，则尝试使用项目根目录下的model目录
            if not Path(model_dir).exists():
                # 获取项目根目录（从当前文件向上两级）
                project_root = Path(__file__).parent.parent
                model_dir = str(project_root / "model")
                
                # 如果还是不存在，尝试从当前文件的路径构建
                if not Path(model_dir).exists():
                    # 尝试使用当前项目的model目录（最常见的情况）
                    current_dir = Path(__file__).parent
                    # 从core目录向上一级到项目根目录
                    project_root = current_dir.parent
                    model_dir = str(project_root / "model")
            
            self.embedding_model_manager = EmbeddingModelManager(model_dir=model_dir)
            
            # 初始化LLM客户端（使用DeepSeek或其他）
            # 这里使用占位符，实际部署时应从配置或环境变量获取API密钥
            try:
                # 首先检查是否有有效的API密钥
                api_key = os.getenv("DEEPSEEK_API_KEY")
                if api_key and len(api_key) > 10:  # 简单验证密钥长度
                    self.llm_client = DeepSeekClient(api_key=api_key)
                else:
                    print("警告: DEEPSEEK_API_KEY 未设置或无效，将使用模拟响应")
                    # 创建一个模拟的客户端或暂时设置为None，等待动态配置
                    self.llm_client = None
            except Exception as e:
                print(f"警告: 无法初始化LLM客户端 - {e}")
                self.llm_client = None
                
            # 初始化RAG服务
            if self.vector_db_proxy and self.embedding_model_manager:
                # 即使LLM客户端不可用，我们也初始化RAG服务，但要处理LLM不可用的情况
                if not self.llm_client:
                    print("警告: LLM客户端不可用，RAG服务将无法生成最终答案")
                
                # 尝试加载默认模型
                available_models = self.embedding_model_manager.list_available_models()
                print(f"可用的嵌入模型: {available_models}")
                
                # 尝试加载bge-m3模型作为默认模型
                default_model_loaded = False
                if "bge-m3" in available_models:
                    default_model_loaded = self.embedding_model_manager.load_model("bge-m3", alias="default")
                    print(f"{'成功' if default_model_loaded else '失败'}加载bge-m3模型作为'default'别名")
                
                # 如果bge-m3不可用，尝试其他可能的模型
                if not default_model_loaded and available_models:
                    fallback_model = available_models[0]
                    default_model_loaded = self.embedding_model_manager.load_model(fallback_model, alias="default")
                    print(f"使用回退模型 {fallback_model} 作为'default'别名: {'成功' if default_model_loaded else '失败'}")
                
                self.rag_config = AskConfig()
                self.rag_service = RAGService(
                    db_proxy=self.vector_db_proxy,
                    embedding_model_manager=self.embedding_model_manager,
                    llm_client=self.llm_client,  # 可能为None
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
        # 添加调用计数
        if not hasattr(self, '_store_vectors_call_count'):
            self._store_vectors_call_count = 0
        self._store_vectors_call_count += 1
        print(f"  [_store_vectors] 第 {self._store_vectors_call_count} 次调用，处理 {len(chunks)} 个文本块...")
        
        print(f"  开始向量化和存储...")
        
        # 检查向量引擎组件是否可用
        if self.batch_processor and self.vector_db_proxy and self.embedding_model_manager:
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
                    "metadata": chunk.get("metadata", {}),
                    "format_metadata": chunk.get("format_metadata", {})
                }
                delivery_data["chunks"].append(chunk_data)
            
            # 使用批量处理器处理数据（只处理向量化，不直接存储到数据库）
            try:
                # 加载模型（使用正确的模型名称）
                if not self.batch_processor._model_loaded:
                    # print(f"[DEBUG] Loading embedding model...")
                    load_result = self.batch_processor.load_model("bge-m3")  # 使用正确的模型名称
                    # print(f"[DEBUG] Model load result: {load_result}")
                
                if not self.batch_processor._model_loaded:
                    raise RuntimeError("Failed to load embedding model")
                
                # 让batch_processor使用服务接口的数据库代理
                original_db_proxy = self.batch_processor.db_proxy
                self.batch_processor.db_proxy = self.vector_db_proxy
                
                # 处理向量化并存储到正确的数据库
                processed_result = self.batch_processor.process_batch(delivery_data)
                
                # 恢复原始数据库代理
                self.batch_processor.db_proxy = original_db_proxy
                
                store_result = processed_result
                
                # 获取处理后的计数（通过服务接口的代理）
                collection_name = f"kb_{knowledge_base_id}"
                try:
                    count_after_processing = self.vector_db_proxy.get_vector_count(collection_name)
                    # print(f"[DEBUG] Count after processing with service proxy: {count_after_processing}")
                except Exception as e:
                    # print(f"[DEBUG] Could not get count after processing: {e}")
                    count_after_processing = 0
                
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
                   knowledge_base_id: Union[str, int],  # 接受字符串或整数类型
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
            
            # 确保knowledge_base_id是字符串类型
            knowledge_base_id_str = str(knowledge_base_id).strip()
            
            # 添加调试信息（注释掉以减少输出）
            # print(f"[DEBUG] Service Interface - Original knowledge_base_id: {knowledge_base_id}")
            # print(f"[DEBUG] Service Interface - Knowledge base ID type: {type(knowledge_base_id)}")
            # print(f"[DEBUG] Service Interface - Processed knowledge_base_id_str: {knowledge_base_id_str}")
            
            # 设置对话状态
            if conversation_state is None:
                conversation_state = ConversationState()
            
            # 确保知识库ID被正确设置到对话状态中
            conversation_state.user_context.knowledge_base_id = knowledge_base_id_str
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
            result["knowledge_base_id"] = knowledge_base_id_str
            
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
                         knowledge_base_id: Union[str, int],  # 接受字符串或整数类型
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