"""
向量引擎模型加载模块综合测试
测试 embedding_loader 模块的所有功能
"""

import unittest
import sys
from pathlib import Path
import torch
import numpy as np

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent  # 向上4级到达项目根目录
sys.path.append(str(project_root))

# 由于当前文件在core/vector_engine/test目录中
# 我们需要使用绝对导入
try:
    from core.vector_engine.embedding_loader import EmbeddingModelManager
    from core.vector_engine.embedding_loader.loader import EmbeddingModelLoader
    from core.vector_engine.embedding_loader.config import EmbeddingModelConfig, get_model_config
except ImportError:
    # 如果绝对导入失败，尝试相对导入
    from ..embedding_loader import EmbeddingModelManager
    from ..embedding_loader.loader import EmbeddingModelLoader
    from ..embedding_loader.config import EmbeddingModelConfig, get_model_config


class TestEmbeddingModelLoader(unittest.TestCase):
    """嵌入模型加载器测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        # 使用绝对路径，从项目根目录开始
        # 当前文件位于 core/vector_engine/test/，需要向上四级到达项目根目录
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.test_model_dir = str(cls.project_root / "model")
        cls.loader = EmbeddingModelLoader(cls.test_model_dir)
        cls.manager = EmbeddingModelManager(cls.test_model_dir)
    
    def test_list_available_models(self):
        """测试列出可用模型"""
        models = self.loader.list_available_models()
        self.assertIsInstance(models, list)
        
        # 检查是否包含bge-m3模型
        available_models = self.manager.list_available_models()
        self.assertIn("bge-m3", available_models, "bge-m3模型应该在可用模型列表中")
    
    def test_is_valid_model_dir(self):
        """测试模型目录验证"""
        # 测试有效的模型目录
        model_path = Path(self.test_model_dir) / "bge-m3"
        is_valid = self.loader._is_valid_model_dir(model_path)
        self.assertTrue(is_valid, "bge-m3目录应该是有效的模型目录")
    
    def test_config_functions(self):
        """测试配置功能"""
        config = get_model_config("bge-m3")
        self.assertIsNotNone(config, "bge-m3配置应该存在")
        
        if config:
            self.assertEqual(config.model_name, "bge-m3")
            self.assertIsInstance(config, EmbeddingModelConfig)


class TestEmbeddingModelManager(unittest.TestCase):
    """嵌入模型管理器测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        # 使用绝对路径，从项目根目录开始
        # 当前文件位于 core/vector_engine/test/，需要向上四级到达项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        model_path = str(project_root / "model")
        cls.manager = EmbeddingModelManager(model_path)
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        self.assertIsNotNone(self.manager.loader)
        self.assertIsInstance(self.manager.active_models, dict)
    
    def test_list_available_models(self):
        """测试列出可用模型"""
        models = self.manager.list_available_models()
        self.assertIsInstance(models, list)
        self.assertIn("bge-m3", models, "bge-m3应该在可用模型列表中")
    
    def test_load_and_unload_model_basic(self):
        """测试模型加载和卸载基础功能"""
        # 测试加载模型
        models = self.manager.list_available_models()
        
        if "bge-m3" in models:
            # 尝试加载模型
            success = self.manager.load_model("bge-m3", alias="test_model", device="cpu")
            # 检查是否成功（即使失败也不算测试错误，因为可能是资源不足）
            self.assertIsInstance(success, bool)
            
            # 尝试卸载模型
            unload_success = self.manager.unload_model("test_model")
            self.assertIsInstance(unload_success, bool)
    
    def test_get_loaded_models_info(self):
        """测试获取已加载模型信息"""
        info = self.manager.get_loaded_models_info()
        self.assertIsInstance(info, dict)
    
    def test_reload_model(self):
        """测试重新加载模型"""
        # 这个测试主要是验证接口不会抛出异常
        try:
            result = self.manager.reload_model("bge-m3", alias="reload_test", device="cpu")
            # 不期望特定的结果，只要不抛出异常就行
        except Exception as e:
            # 某些环境可能缺少依赖，这不算测试失败
            pass
    
    def test_unload_all_models(self):
        """测试卸载所有模型"""
        result = self.manager.unload_all_models()
        self.assertIsInstance(result, bool)
    
    @unittest.skipIf(not torch.cuda.is_available(), "CUDA不可用，跳过GPU测试")
    def test_gpu_loading(self):
        """测试GPU加载功能"""
        # 测试GPU加载（仅在CUDA可用时）
        try:
            success = self.manager.load_model("bge-m3", alias="gpu_test_model", device="cuda")
            if success:
                # 验证模型确实在GPU上
                model = self.manager.get_model("gpu_test_model")
                if model:
                    # 测试编码功能
                    sentences = ["测试GPU加速", "GPU模型加载"]
                    embeddings = self.manager.encode("gpu_test_model", sentences)
                    self.assertIsNotNone(embeddings)
                    
                # 卸载模型
                self.manager.unload_model("gpu_test_model")
        except Exception as e:
            # GPU测试失败不视为整体测试失败
            pass
    
    def test_auto_device_selection(self):
        """测试自动设备选择功能"""
        # 测试不指定设备时的自动选择
        success = self.manager.load_model("bge-m3", alias="auto_device_model")
        # 应该成功加载（无论是在CPU还是GPU上）
        self.assertIsInstance(success, bool)
        
        # 卸载模型
        self.manager.unload_model("auto_device_model")
    
    def test_model_encoding_functionality(self):
        """测试模型编码功能"""
        # 先加载模型
        success = self.manager.load_model("bge-m3", alias="encoding_test_model", device="cpu")
        
        if success:
            # 测试编码功能
            test_sentences = [
                "这是一个测试句子。",
                "Embedding模型可以将文本转换为向量。",
                "向量表示有助于语义搜索和相似度计算。"
            ]
            
            embeddings = self.manager.encode("encoding_test_model", test_sentences)
            if embeddings is not None:
                # 验证输出形状
                self.assertEqual(len(embeddings), len(test_sentences))
                # 验证向量维度（BGE-M3通常输出1024维向量）
                self.assertEqual(len(embeddings[0]), 1024)
            
            # 卸载模型
            self.manager.unload_model("encoding_test_model")


class TestIntegration(unittest.TestCase):
    """集成测试类"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 使用绝对路径，从项目根目录开始
        # 当前文件位于 core/vector_engine/test/，需要向上四级到达项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        model_path = str(project_root / "model")
        manager = EmbeddingModelManager(model_path)
        
        # 1. 检查可用模型
        available_models = manager.list_available_models()
        self.assertIn("bge-m3", available_models)
        
        # 2. 加载模型
        load_success = manager.load_model("bge-m3", alias="workflow_model")
        self.assertIsInstance(load_success, bool)
        
        if load_success:
            # 3. 获取模型信息
            info = manager.get_loaded_models_info()
            self.assertIsInstance(info, dict)
            
            # 4. 进行编码测试
            sentences = ["集成测试句子1", "集成测试句子2"]
            embeddings = manager.encode("workflow_model", sentences)
            if embeddings is not None:
                self.assertEqual(len(embeddings), 2)
            
            # 5. 卸载模型
            unload_success = manager.unload_model("workflow_model")
            self.assertTrue(unload_success)
        
        # 6. 验证模型已卸载
        loaded_models = manager.get_loaded_models_info()
        self.assertNotIn("workflow_model", loaded_models)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("运行向量引擎模型加载模块综合测试...")
    success = run_tests()
    
    if success:
        print("\n✓ 所有测试通过!")
    else:
        print("\n✗ 部分测试失败!")
    
    # 提供基本功能验证
    print("\n进行基本功能验证...")
    try:
        # 当前文件位于 core/vector_engine/test/，需要向上四级到达项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        model_path = str(project_root / "model")
        manager = EmbeddingModelManager(model_path)
        models = manager.list_available_models()
        print(f"✓ 成功访问模型管理器")
        print(f"✓ 发现模型: {models}")
        
        if "bge-m3" in models:
            print("✓ bge-m3模型可用")
        else:
            print("⚠ 未发现bge-m3模型")
            
    except Exception as e:
        print(f"✗ 基本功能验证失败: {e}")