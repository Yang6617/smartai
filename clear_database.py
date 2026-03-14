#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清空数据库和向量数据库脚本（非交互式版本）

此脚本用于清空：
1. SQLite数据库（删除数据库文件）
2. ChromaDB向量数据库（清空所有向量数据）

警告: 此操作不可恢复！
"""

import os
import sys
import shutil
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.vector_engine.vector_db_proxy.config import VectorDBConfig
from core.vector_engine.vector_db_proxy.chromadb_adapter import ChromaDBAdapter


def clear_sqlite_database(force=False):
    """
    清空SQLite数据库
    删除数据库文件，下次运行时会自动重新创建
    """
    print("=" * 60)
    print("清空 SQLite 数据库")
    print("=" * 60)
    
    # 从环境变量获取数据库路径
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL", None)
    
    # 如果没有设置 DATABASE_URL，使用与 db_config.py 相同的默认路径
    if database_url is None:
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent
        database_url = f"sqlite:///{base_dir / 'backend' / 'fastapi_project' / 'knowledge_system.db'}"
    
    # 提取数据库文件路径（对于SQLite）
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        db_full_path = Path(db_path).resolve()
        
        if db_full_path.exists():
            try:
                db_full_path.unlink()
                print(f"✓ 成功删除数据库文件: {db_full_path}")
                print("  注意: 下次运行时会自动重新创建数据库结构")
                return True
            except Exception as e:
                print(f"✗ 删除数据库文件失败: {e}")
                return False
        else:
            print(f"! 数据库文件不存在: {db_full_path}")
            print("  无需清空操作")
            return True
    else:
        print(f"! 非SQLite数据库，无法自动清空: {database_url}")
        print("  请手动清空该数据库")
        return False


def clear_chromadb(force=False):
    """
    清空ChromaDB向量数据库
    删除向量数据库文件夹，下次运行时会自动重新创建
    """
    print("\n" + "=" * 60)
    print("清空 ChromaDB 向量数据库")
    print("=" * 60)
    
    # 配置数据库连接
    config = VectorDBConfig(
        db_type="chromadb",
        path="./chroma_data",  # 使用与VectorDBConfig相同的默认路径
        host="",
        port=0,
        pool_size=2,
        max_overflow=5
    )
    
    # 获取数据库路径
    db_path = Path(config.path).resolve()
    
    if db_path.exists():
        try:
            # 删除整个数据库文件夹
            shutil.rmtree(db_path)
            print(f"✓ 成功删除向量数据库文件夹: {db_path}")
            print("  注意: 下次运行时会自动重新创建向量数据库")
            return True
        except Exception as e:
            print(f"✗ 删除向量数据库文件夹失败: {e}")
            return False
    else:
        print(f"! 向量数据库文件夹不存在: {db_path}")
        print("  无需清空操作")
        return True


def clear_all():
    """
    清空所有数据库
    """
    print("\n" + "=" * 60)
    print("灵析知识库 - 清空数据库（非交互式）")
    print("=" * 60)
    print("\n警告: 此操作将清空所有数据，且不可恢复！")
    print("\n将清空:")
    print("  1. SQLite数据库（包含用户、文件、问答记录等）")
    print("  2. ChromaDB向量数据库（包含所有向量数据）")
    print("=" * 60)
    
    # 清空SQLite数据库
    sqlite_success = clear_sqlite_database(force=True)
    
    # 清空ChromaDB向量数据库
    chromadb_success = clear_chromadb(force=True)
    
    # 总结
    print("\n" + "=" * 60)
    print("清空操作完成")
    print("=" * 60)
    
    if sqlite_success and chromadb_success:
        print("✓ 所有数据库已成功清空")
        print("\n提示: 下次运行演示脚本时，系统会自动重新创建数据库结构")
        return True
    else:
        print("✗ 部分数据库清空失败，请检查错误信息")
        return False


if __name__ == "__main__":
    success = clear_all()
    
    if not success:
        sys.exit(1)