"""
脚本：初始化 ChromaDB 向量数据库（持久化模式）
根据 db_design.md 中的设计创建数据库和集合
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.chromadb_adapter import ChromaDBAdapter


def init_chromadb_persistent():
    """
    使用持久化模式初始化 ChromaDB 数据库
    """
    print("正在初始化 ChromaDB 持久化数据库...")
    
    # 配置数据库连接（使用持久化模式）
    config = VectorDBConfig(
        db_type="chromadb",
        path="./chroma_data",  # 使用与VectorDBConfig相同的默认路径
        host="",  # 留空以使用持久化模式
        port=0,   # 留空以使用持久化模式
        pool_size=2,
        max_overflow=5
    )
    
    # 直接使用适配器，避免连接池初始化问题
    adapter = ChromaDBAdapter(config)
    
    try:
        # 连接到数据库（持久化模式）
        if adapter.connect():
            print("✓ 成功连接到 ChromaDB 持久化数据库")
        else:
            print("✗ 连接 ChromaDB 持久化数据库失败")
            return False
        
        # 创建默认集合
        collection_name = "knowledge_base_chunks"
        if adapter.create_collection(
            collection_name=collection_name,
            metadata={
                "description": "知识库文本片段向量集合",
                "schema_version": "1.0",
                "created_at": datetime.now().isoformat()
            }
        ):
            print(f"✓ 成功创建集合: {collection_name}")
        else:
            print(f"✗ 创建集合 {collection_name} 失败")
            return False
        
        # 添加一些示例数据来验证数据库结构
        sample_embedding = [0.1] * 768  # 模拟 BGE-M3 生成的 768 维向量
        sample_document = "这是一个示例文本片段，用于验证数据库结构。"
        
        sample_metadata = {
            "document_id": "sample_doc_001",
            "chunk_index": 0,
            "source_type": "markdown",
            "source_info": "# 示例标题",
            "knowledge_base_id": "default_kb",
            "uploader_id": "system",
            "version": 1,
            "timestamp": datetime.now().isoformat()
        }
        
        sample_id = f"sample_chunk_{uuid.uuid4().hex[:8]}"
        
        if adapter.add_vectors(
            collection_name=collection_name,
            vectors=[sample_embedding],
            ids=[sample_id],
            documents=[sample_document],
            metadatas=[sample_metadata]
        ):
            print("✓ 成功添加示例数据")
        else:
            print("✗ 添加示例数据失败")
            return False
        
        # 验证数据插入
        vector_count = adapter.get_vector_count(collection_name)
        print(f"✓ 集合 {collection_name} 中的向量数量: {vector_count}")
        
        # 进行一次简单的相似度搜索测试
        results = adapter.query_vectors(
            collection_name=collection_name,
            query_vector=sample_embedding,
            n_results=1
        )
        
        if results:
            print("✓ 相似度搜索测试成功")
            print(f"  返回结果数量: {len(results)}")
            if results:
                print(f"  第一个结果ID: {results[0]['id']}")
        else:
            print("✗ 相似度搜索测试失败")
            return False
        
        print("\n✓ ChromaDB 持久化数据库初始化完成!")
        print(f"  数据文件保存在: {(Path(config.path).resolve())}")
        return True
        
    except Exception as e:
        print(f"✗ 初始化过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 断开连接
        try:
            adapter.disconnect()
            print("✓ 已断开数据库连接")
        except Exception as e:
            print(f"断开连接时出现错误: {str(e)}")


def create_sample_data_for_kb_direct(knowledge_base_id: str, num_samples: int = 5):
    """
    为特定知识库创建示例数据（直接使用适配器）
    
    Args:
        knowledge_base_id: 知识库ID
        num_samples: 示例数据数量
    """
    config = VectorDBConfig(
        db_type="chromadb",
        path="./chroma_data",
        host="",  # 留空以使用持久化模式
        port=0
    )
    adapter = ChromaDBAdapter(config)
    
    try:
        adapter.connect()
        
        collection_name = "knowledge_base_chunks"
        
        for i in range(num_samples):
            # 模拟 BGE-M3 生成的向量
            embedding = [float((i + j) % 100) / 100.0 for j in range(768)]
            
            document = f"这是来自知识库 {knowledge_base_id} 的第 {i+1} 个文本片段。"
            
            metadata = {
                "document_id": f"{knowledge_base_id}_doc_{i:03d}",
                "chunk_index": i,
                "source_type": "markdown",
                "source_info": f"# 章节 {i+1}",
                "knowledge_base_id": knowledge_base_id,
                "uploader_id": "demo_user",
                "version": 1,
                "timestamp": datetime.now().isoformat()
            }
            
            chunk_id = f"{knowledge_base_id}_chunk_{i:03d}_{uuid.uuid4().hex[:6]}"
            
            success = adapter.add_vectors(
                collection_name=collection_name,
                vectors=[embedding],
                ids=[chunk_id],
                documents=[document],
                metadatas=[metadata]
            )
            
            if success:
                print(f"  ✓ 添加示例数据 {i+1}/{num_samples}: {chunk_id}")
            else:
                print(f"  ✗ 添加示例数据 {i+1}/{num_samples} 失败")
        
        print(f"✓ 为知识库 {knowledge_base_id} 添加了 {num_samples} 个示例数据")
        
    except Exception as e:
        print(f"✗ 为知识库 {knowledge_base_id} 创建示例数据时出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            adapter.disconnect()
        except:
            pass


if __name__ == "__main__":
    print("=" * 60)
    print("ChromaDB 持久化向量数据库初始化脚本")
    print("使用本地持久化模式，无需启动单独的服务器")
    print("=" * 60)
    
    # 初始化数据库（持久化模式）
    success = init_chromadb_persistent()
    
    if success:
        print("\n" + "=" * 60)
        print("为演示目的添加一些示例数据...")
        print("=" * 60)
        
        # 为不同的知识库添加示例数据
        create_sample_data_for_kb_direct("team_ai_research", 3)
        create_sample_data_for_kb_direct("product_manuals", 4)
        create_sample_data_for_kb_direct("customer_support", 2)
        
        print("\n" + "=" * 60)
        print("数据库初始化和示例数据添加完成！")
        print("数据文件保存在: ./chroma_persistent_data")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("数据库初始化失败，请检查错误信息。")
        print("=" * 60)