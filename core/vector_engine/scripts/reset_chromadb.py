"""
脚本：重置 ChromaDB 向量数据库（清空所有数据，仅保留结构）
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.chromadb_adapter import ChromaDBAdapter


def reset_chromadb():
    """
    重置 ChromaDB 数据库，清空所有数据
    """
    print("正在重置 ChromaDB 数据库...")
    
    # 配置数据库连接
    config = VectorDBConfig(
        db_type="chromadb",
        path="./chroma_data",  # 使用与VectorDBConfig相同的默认路径
        host="",  # 留空以使用持久化模式
        port=0,   # 留空以使用持久化模式
        pool_size=2,
        max_overflow=5
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
        
        # 删除现有集合（如果有）
        collection_name = "knowledge_base_chunks"
        try:
            if adapter.delete_collection(collection_name):
                print(f"✓ 成功删除集合: {collection_name}")
            else:
                print(f"! 集合 {collection_name} 不存在，无需删除")
        except Exception as e:
            print(f"! 删除集合时出现错误（可能因为集合不存在）: {str(e)}")
        
        # 重新创建集合（空的）
        if adapter.create_collection(
            collection_name=collection_name,
            metadata={
                "description": "知识库文本片段向量集合",
                "schema_version": "1.0",
                "created_at": datetime.now().isoformat(),
                "note": "此集合用于存储知识库的文本片段向量"
            }
        ):
            print(f"✓ 重新创建空集合: {collection_name}")
        else:
            print(f"✗ 重新创建集合 {collection_name} 失败")
            return False
        
        # 验证集合为空
        count = adapter.get_vector_count(collection_name)
        print(f"✓ 集合 {collection_name} 当前向量数量: {count}")
        
        if count == 0:
            print("✓ 数据库重置成功：集合已清空")
        else:
            print(f"⚠ 警告：集合中仍有 {count} 个向量")
        
        print(f"  数据库文件位置: {(Path(config.path).resolve())}")
        return True
        
    except Exception as e:
        print(f"✗ 重置过程中出现错误: {str(e)}")
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
    print("ChromaDB 数据库重置脚本")
    print("(清空所有数据，仅保留数据库结构)")
    print("=" * 60)
    
    success = reset_chromadb()
    
    if success:
        print("\n" + "=" * 60)
        print("数据库重置完成！")
        print("数据库结构已保留，但集合中无数据。")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("数据库重置失败，请检查错误信息。")
        print("=" * 60)