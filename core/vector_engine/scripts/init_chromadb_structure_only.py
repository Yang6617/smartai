"""
脚本：初始化 ChromaDB 向量数据库（仅创建结构，不写入数据）
根据 db_design.md 中的设计创建数据库和集合
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.chromadb_adapter import ChromaDBAdapter


def init_chromadb_structure_only():
    """
    仅初始化 ChromaDB 数据库结构，不添加任何示例数据
    """
    print("正在初始化 ChromaDB 数据库结构...")
    
    # 配置数据库连接（使用持久化模式）
    config = VectorDBConfig(
        db_type="chromadb",
        path="../../data/chroma_persistent_data",  # 本地持久化路径
        host="",  # 留空以使用持久化模式
        port=0,   # 留空以使用持久化模式
        pool_size=2,
        max_overflow=5
    )
    
    # 直接使用适配器
    adapter = ChromaDBAdapter(config)
    
    try:
        # 连接到数据库（持久化模式）
        if adapter.connect():
            print("✓ 成功连接到 ChromaDB 持久化数据库")
        else:
            print("✗ 连接 ChromaDB 持久化数据库失败")
            return False
        
        # 创建默认集合（如果不存在）
        collection_name = "knowledge_base_chunks"
        try:
            if adapter.create_collection(
                collection_name=collection_name,
                metadata={
                    "description": "知识库文本片段向量集合",
                    "schema_version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "note": "此集合用于存储知识库的文本片段向量"
                }
            ):
                print(f"✓ 成功创建集合: {collection_name}")
                print(f"  集合描述: 知识库文本片段向量集合")
            else:
                print(f"! 集合 {collection_name} 已存在，跳过创建")
        except Exception as e:
            if "already exists" in str(e):
                print(f"! 集合 {collection_name} 已存在，无需重复创建")
            else:
                print(f"✗ 创建集合 {collection_name} 失败: {str(e)}")
                return False
                
        print(f"  数据库文件位置: {os.path.abspath(config.path)}")
        
        print("\n✓ ChromaDB 数据库结构创建完成!")
        print("  提示: 数据库已准备好，但集合为空，等待实际数据写入。")
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


if __name__ == "__main__":
    print("=" * 60)
    print("ChromaDB 数据库结构初始化脚本")
    print("(仅创建数据库和集合，不写入任何示例数据)")
    print("=" * 60)
    
    success = init_chromadb_structure_only()
    
    if success:
        print("\n" + "=" * 60)
        print("数据库结构初始化完成！")
        print("数据库已创建，集合已准备就绪，但集合中无数据。")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("数据库结构初始化失败，请检查错误信息。")
        print("=" * 60)