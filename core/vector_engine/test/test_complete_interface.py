"""
完整验证接口文档中的所有功能
"""
import sys
import os

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.proxy import VectorDBProxy, create_vector_db_proxy
import uuid
from datetime import datetime

def test_complete_interface():
    print("=== 完整接口功能验证 ===")
    
    # 使用推荐的方式创建代理
    proxy = create_vector_db_proxy(
        db_type="chromadb",
        path="../../chroma_data",
        host="",
        port=0
    )
    
    try:
        print("1. 测试连接管理...")
        connected = proxy.connect()
        print(f"   连接状态: {connected}")
        
        print("\n2. 测试集合管理...")
        # 获取当前向量数量
        initial_count = proxy.get_vector_count("knowledge_base_chunks")
        print(f"   初始向量数量: {initial_count}")
        
        print("\n3. 测试向量操作...")
        # 添加一个测试向量
        test_embedding = [0.1] * 768  # 模拟768维向量
        test_id = f"test_vector_{uuid.uuid4().hex[:8]}"
        test_document = "这是用于测试的向量数据。"
        test_metadata = {
            "document_id": f"doc_{uuid.uuid4().hex[:8]}",
            "chunk_index": 0,
            "source_type": "test",
            "knowledge_base_id": "test_kb",
            "uploader_id": "test_user",
            "version": 1,
            "timestamp": datetime.now().isoformat()
        }
        
        add_success = proxy.add_vectors(
            collection_name="knowledge_base_chunks",
            vectors=[test_embedding],
            ids=[test_id],
            documents=[test_document],
            metadatas=[test_metadata]
        )
        print(f"   添加向量成功: {add_success}")
        
        # 验证向量数量变化
        after_add_count = proxy.get_vector_count("knowledge_base_chunks")
        print(f"   添加后向量数量: {after_add_count}")
        print(f"   数量变化: {after_add_count - initial_count}")
        
        # 查询刚添加的向量
        query_results = proxy.query_vectors(
            collection_name="knowledge_base_chunks",
            query_vector=test_embedding,
            n_results=1
        )
        print(f"   查询结果数量: {len(query_results) if query_results else 0}")
        
        print("\n4. 测试统计功能...")
        stats = proxy.get_stats()
        print(f"   统计信息包含: {list(stats.keys())}")
        print(f"   连接池状态: {stats['pool_stats']}")
        print(f"   性能指标: {stats['performance_metrics']}")
        print(f"   健康状况: {stats['is_healthy']}")
        
        print("\n5. 测试删除操作...")
        # 删除刚才添加的向量
        delete_success = proxy.delete_vectors(
            collection_name="knowledge_base_chunks",
            ids=[test_id]
        )
        print(f"   删除向量成功: {delete_success}")
        
        # 验证删除后数量
        final_count = proxy.get_vector_count("knowledge_base_chunks")
        print(f"   删除后向量数量: {final_count}")
        print(f"   最终数量变化: {final_count - initial_count}")
        
        print("\n=== 所有接口功能验证完成！ ===")
        
    except Exception as e:
        print(f"接口功能验证出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        proxy.disconnect()

if __name__ == "__main__":
    test_complete_interface()