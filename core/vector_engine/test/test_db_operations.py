"""
脚本：测试 ChromaDB 向量数据库操作
验证根据 db_design.md 设计的数据结构
"""

import os
import sys
import uuid
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.vector_engine.vector_db_proxy.chromadb_adapter import ChromaDBAdapter
from core.vector_engine.vector_db_proxy.config import VectorDBConfig


def test_chromadb_operations():
    """
    测试 ChromaDB 数据库的各种操作
    """
    print("正在测试 ChromaDB 数据库操作...")
    
    # 配置数据库连接（使用持久化模式）
    config = VectorDBConfig(
        db_type="chromadb",
        path="../../data/chroma_persistent_data",  # 本地持久化路径
        host="",  # 留空以使用持久化模式
        port=0,   # 留空以使用持久化模式
    )
    
    # 直接使用适配器
    adapter = ChromaDBAdapter(config)
    
    try:
        # 连接到数据库
        if adapter.connect():
            print("✓ 成功连接到 ChromaDB 持久化数据库")
        else:
            print("✗ 连接 ChromaDB 持久化数据库失败")
            return False
        
        collection_name = "knowledge_base_chunks"
        
        # 测试：获取现有集合或创建新集合
        try:
            collection = adapter.get_collection(collection_name)
            if collection:
                print(f"✓ 成功获取集合: {collection_name}")
            else:
                print(f"集合 {collection_name} 不存在，尝试创建...")
                if adapter.create_collection(collection_name):
                    print(f"✓ 成功创建集合: {collection_name}")
                else:
                    print(f"✗ 创建集合 {collection_name} 失败")
                    return False
        except Exception as e:
            print(f"获取/创建集合时出错: {str(e)}")
            # 尝试创建集合
            if adapter.create_collection(collection_name):
                print(f"✓ 成功创建集合: {collection_name}")
            else:
                print(f"✗ 创建集合 {collection_name} 失败")
                return False
        
        # 验证当前集合中的向量数量
        initial_count = adapter.get_vector_count(collection_name)
        print(f"✓ 集合初始向量数量: {initial_count}")
        
        # 测试：添加符合设计规范的新数据
        print("\n--- 测试添加数据 ---")
        
        # 模拟 BGE-M3 生成的 768 维向量
        sample_embedding = [round(0.1 + i * 0.01, 3) for i in range(768)]
        sample_document = "人工智能是计算机科学的一个分支，致力于构建能够执行人类智能任务的机器。"

        # 根据 db_design.md 中的元数据规范创建元数据
        sample_metadata = {
            "document_id": f"doc_{uuid.uuid4().hex[:8]}",  # 唯一文档ID
            "chunk_index": 0,  # 文档中的索引
            "source_type": "markdown",  # 源文件类型
            "source_info": "# 人工智能概述",  # 位置信息
            "knowledge_base_id": "ai_research_kb",  # 知识库ID
            "uploader_id": "test_user",  # 上传者ID
            "version": 1,  # 版本号
            "timestamp": datetime.now().isoformat()  # 时间戳
        }

        # 生成唯一ID
        sample_id = f"chunk_{uuid.uuid4().hex[:12]}"
        
        print(f"准备添加数据 - ID: {sample_id}")
        print(f"向量维度: {len(sample_embedding)}")
        print(f"文档长度: {len(sample_document)} 字符")
        print(f"元数据字段数: {len(sample_metadata)}")
        
        if adapter.add_vectors(
            collection_name=collection_name,
            vectors=[sample_embedding],
            ids=[sample_id],
            documents=[sample_document],
            metadatas=[sample_metadata]
        ):
            print("✓ 成功添加向量数据")
        else:
            print("✗ 添加向量数据失败")
            return False

        # 验证添加后的向量数量
        after_add_count = adapter.get_vector_count(collection_name)
        print(f"✓ 添加后向量数量: {after_add_count}")
        print(f"✓ 预期增加: {after_add_count - initial_count}")

        # 测试：查询刚刚添加的数据
        print("\n--- 测试查询数据 ---")
        
        # 进行相似度搜索测试
        results = adapter.query_vectors(
            collection_name=collection_name,
            query_vector=sample_embedding,
            n_results=2  # 查询2个结果
        )

        if results:
            print(f"✓ 相似度搜索成功，返回 {len(results)} 个结果")
            for i, result in enumerate(results):
                print(f"  结果 {i+1}:")
                print(f"    ID: {result.get('id', 'N/A')}")
                print(f"    距离: {result.get('distance', 'N/A')}")
                print(f"    文档预览: {result.get('document', 'N/A')[:50]}...")
                print(f"    元数据: {result.get('metadata', {})}")
        else:
            print("✗ 相似度搜索未返回结果")
            # 再次检查向量数量
            current_count = adapter.get_vector_count(collection_name)
            print(f"当前集合中的向量数量: {current_count}")

        # 测试：添加更多样例数据以验证不同知识库的隔离
        print("\n--- 测试多知识库数据添加 ---")
        
        kb_ids = ["tech_docs", "research_papers", "user_manuals"]
        
        for idx, kb_id in enumerate(kb_ids):
            embedding = [round(0.2 + idx + i * 0.01, 3) for i in range(768)]
            document = f"这是来自 {kb_id} 知识库的样本文档 #{idx+1}。"
            
            metadata = {
                "document_id": f"{kb_id}_doc_{idx:03d}",
                "chunk_index": idx,
                "source_type": "pdf" if "paper" in kb_id else "markdown",
                "source_info": f"Section {idx+1}",
                "knowledge_base_id": kb_id,
                "uploader_id": f"user_{idx+1}",
                "version": 1,
                "timestamp": datetime.now().isoformat()
            }
            
            chunk_id = f"{kb_id}_chunk_{uuid.uuid4().hex[:8]}"
            
            success = adapter.add_vectors(
                collection_name=collection_name,
                vectors=[embedding],
                ids=[chunk_id],
                documents=[document],
                metadatas=[metadata]
            )
            
            if success:
                print(f"  ✓ 添加 {kb_id} 知识库数据: {chunk_id}")
            else:
                print(f"  ✗ 添加 {kb_id} 知识库数据失败")
        
        # 最终验证
        final_count = adapter.get_vector_count(collection_name)
        print(f"\n✓ 最终集合向量数量: {final_count}")
        
        # 测试：基于知识库ID的过滤查询
        print("\n--- 测试基于知识库的过滤查询 ---")
        
        # 查询特定知识库的数据
        tech_results = adapter.query_vectors(
            collection_name=collection_name,
            query_vector=[0.5] * 768,  # 随意向量
            n_results=5,
            where={"knowledge_base_id": "tech_docs"}
        )
        
        print(f"技术文档知识库查询结果: {len(tech_results)} 项")
        
        print("\n✓ 所有测试完成！")
        return True

    except Exception as e:
        print(f"✗ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 断开连接
        try:
            adapter.disconnect()
            print("\n✓ 已断开数据库连接")
        except Exception as e:
            print(f"断开连接时出现错误: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("ChromaDB 数据库操作测试脚本")
    print("验证 db_design.md 中定义的数据结构")
    print("=" * 60)
    
    success = test_chromadb_operations()
    
    if success:
        print("\n" + "=" * 60)
        print("数据库操作测试成功完成！")
        print("数据库文件保存在: ./chroma_persistent_data")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("数据库操作测试失败。")
        print("=" * 60)