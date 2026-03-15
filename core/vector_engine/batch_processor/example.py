"""
示例：使用批量向量化处理模块
"""
import sys
from pathlib import Path
import json

def main():
    # 添加项目根目录到系统路径
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from .config import BatchProcessorConfig
    from .processor import BatchVectorProcessor
    
    # 创建配置
    config = BatchProcessorConfig(
        model_path="../../model",  # 模型存储路径
        db_path="../../chroma_data"  # 向量数据库路径
    )
    
    # 创建批量处理器
    processor = BatchVectorProcessor(config)
    
    # 准备示例数据
    delivery_data = {
        "document_id": "doc_001", 
        "team_id": "team_abc", 
        "user_id": "user_1234",
        "file_name": "产品介绍.md", 
        "file_type": "markdown", 
        "chunks": [
            {
                "text": "我们的产品支持实时协作功能，让团队成员能够同时编辑文档。",
                "chunk_index": 0, 
                "structure_path": ["# 功能特色", "## 核心优势"],  # 结构化位置 
            }, 
            {
                "text": "系统延迟低于100ms，确保流畅的用户体验。",
                "chunk_index": 1, 
                "structure_path": ["# 功能特色", "## 性能指标"], 
            },
            {
                "text": "支持多种文件格式导入，包括Word、PDF和Markdown。",
                "chunk_index": 2, 
                "structure_path": ["# 功能特色", "## 兼容性"], 
            }
        ] 
    }
    
    try:
        # 加载模型
        print("正在加载模型...")
        success = processor.load_model("bge-m3", alias="main_embedding_model")
        if not success:
            print("模型加载失败")
            return
        
        print("模型加载成功")
        
        # 处理批量数据
        print("正在处理批量数据...")
        result = processor.process_batch(delivery_data, model_alias="main_embedding_model")
        
        print(f"处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 卸载模型
        processor.unload_model("main_embedding_model")
        print("模型已卸载")
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()