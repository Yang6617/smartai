#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
灵析知识库 - 清晰功能演示脚本

此脚本演示了灵析知识库系统的主要功能，专注于展示问题和答案，
减少调试信息，提供清晰的演示体验。
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 从核心服务导入接口
from core.service_interface import upload_file_interface, ask_question_interface





def demo_upload_and_query():
    """
    演示上传文件和提问的主要功能（精简版）
    """
    print("=" * 60)
    print("灵析知识库 - 功能演示（精简版）")
    print("=" * 60)
    
    # 使用预存的示例文档
    sample_doc_path = "demo_document.md"
    print(f"\n📋 使用预存示例文档: {sample_doc_path}")
    
    # 步骤1: 上传文档
    print("\n📁 步骤 1: 上传文档到知识库")
    print(f"   正在上传文件: {sample_doc_path}")
    
    start_time = time.time()
    upload_result = upload_file_interface(
        file_path=sample_doc_path,
        user_id="demo_user_001",
        knowledge_base_id="kb_demo_001",
        file_name="demo_document.md",
        custom_metadata={
            "category": "technology",
            "topic": "artificial_intelligence",
            "language": "zh-CN",
            "tags": ["AI", "machine_learning", "deep_learning", "NLP"]
        }
    )
    upload_duration = time.time() - start_time
    
    if upload_result.get('status') != 'success':
        print(f"   ❌ 上传失败: {upload_result.get('message', 'Unknown error')}")
        return
    
    print(f"   ✓ 上传成功! 耗时: {upload_duration:.2f}秒")
    print(f"   文档ID: {upload_result.get('document_id', 'N/A')}")
    print(f"   处理元素数: {upload_result.get('processed_elements_count', 0)}")
    
    # 步骤2: 等待向量处理完成
    print("\n⏳ 步骤 2: 等待向量处理完成")
    time.sleep(2)  # 等待向量数据库索引完成
    
    # 步骤4: 提问并获取答案（重点关注问题和答案）
    print("\n💬 步骤 4: 基于知识库提问 - 问题与答案展示")
    
    questions = [
        "人工智能的主要技术分支有哪些？",
        "什么是机器学习？",
        "深度学习和机器学习有什么区别？",
        "人工智能有哪些应用领域？",
        "自然语言处理是做什么的？",
        "人工智能发展历程中有哪些重要节点？",
        "未来人工智能的发展趋势是什么？"
    ]
    
    print(f"\n共 {len(questions)} 个问题及其答案:")
    print("-" * 60)
    
    for i, question in enumerate(questions, 1):
        print(f"\n【问题 {i}】\n{question}")
        
        start_time = time.time()
        response = ask_question_interface(
            question=question,
            user_id="demo_user_001",
            knowledge_base_id="kb_demo_clean_001",
            model_alias="default",
            top_k=5
        )
        query_duration = time.time() - start_time
        
        # 显示答案
        answer = response.get('answer', '未能获取答案')
        confidence = response.get('confidence_score', 0)
        
        print(f"【答案】\n{answer}")
        print(f"\n【置信度】: {confidence:.2f} | 【查询耗时】: {query_duration:.2f}秒")
        print("-" * 60)
    
    print("\n🎉 演示完成! 以上展示了灵析知识库系统的主要功能。")
    print("=" * 60)


def main():
    """
    主函数
    """
    try:
        demo_upload_and_query()
    except KeyboardInterrupt:
        print("\n⚠ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()