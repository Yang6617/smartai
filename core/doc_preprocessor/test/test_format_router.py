"""
格式路由分发模块的单元测试
"""
import unittest
import tempfile
import os
from pathlib import Path
from core.doc_preprocessor.format_router import (
    FileTypeIdentifier, 
    StrategySelector, 
    ParseStrategy, 
    TaskQueue, 
    Task, 
    Priority, 
    FormatRouter
)


class TestFileTypeIdentifier(unittest.TestCase):
    """测试文件类型识别功能"""
    
    def setUp(self):
        self.identifier = FileTypeIdentifier()
    
    def test_identify_txt_file(self):
        """测试识别TXT文件"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test content')
            temp_file = f.name
        
        try:
            mime_type, ext, confidence = self.identifier.identify_file_type(temp_file)
            self.assertEqual(ext, '.txt')
            self.assertIn('text', mime_type)
            self.assertGreaterEqual(confidence, 0.8)
        finally:
            os.unlink(temp_file)
    
    def test_identify_pdf_file(self):
        """测试识别PDF文件"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            # 写入PDF文件头
            f.write(b'%PDF-1.4\n')
            temp_file = f.name
        
        try:
            mime_type, ext, confidence = self.identifier.identify_file_type(temp_file)
            self.assertEqual(ext, '.pdf')
            self.assertIn('pdf', mime_type.lower())
            self.assertGreaterEqual(confidence, 0.8)
        finally:
            os.unlink(temp_file)


class TestStrategySelector(unittest.TestCase):
    """测试策略选择功能"""
    
    def setUp(self):
        self.selector = StrategySelector()
    
    def test_select_strategy_small_text_file(self):
        """测试小文本文件的策略选择"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Small test content')
            temp_file = f.name
        
        try:
            config = self.selector.select_strategy(temp_file, 'text/plain')
            # 小文件应该使用快速解析
            self.assertIn(config.strategy, [ParseStrategy.QUICK_PARSE, ParseStrategy.BALANCED_PARSE])
        finally:
            os.unlink(temp_file)
    
    def test_select_strategy_large_file(self):
        """测试大文件的策略选择"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            # 创建较大的文件（超过小文件阈值）
            f.write(b'A' * (1024 * 1024))  # 1MB文件
            temp_file = f.name
        
        try:
            config = self.selector.select_strategy(temp_file, 'text/plain')
            # 大文件应该使用平衡或深度解析
            self.assertIn(config.strategy, [ParseStrategy.BALANCED_PARSE, ParseStrategy.DEEP_PARSE])
        finally:
            os.unlink(temp_file)


class TestTaskQueue(unittest.TestCase):
    """测试任务队列功能"""
    
    def setUp(self):
        self.queue = TaskQueue(max_workers=2)
    
    def test_submit_and_process_task(self):
        """测试提交和处理任务"""
        def mock_processor(task):
            return f"Processed {task.file_path}"
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test content')
            temp_file = f.name
        
        try:
            task = Task(
                task_id="test_task_1",
                file_path=temp_file,
                user_id="user1",
                team_id="team1",
                priority=Priority.NORMAL,
                submit_time=1234567890.0
            )
            
            task_id = self.queue.submit_task(task)
            self.assertEqual(task_id, "test_task_1")
            
            # 处理任务
            processed = self.queue.process_next_task(mock_processor)
            self.assertTrue(processed)
            
            # 检查结果
            result = self.queue.get_task_result("test_task_1")
            self.assertEqual(result, f"Processed {temp_file}")
        finally:
            os.unlink(temp_file)
    
    def test_priority_handling(self):
        """测试优先级处理"""
        def mock_processor(task):
            return f"Priority: {task.priority.name}"
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test content')
            temp_file = f.name
        
        try:
            # 提交低优先级任务
            low_task = Task(
                task_id="low_task",
                file_path=temp_file,
                user_id="user1",
                team_id="team1",
                priority=Priority.LOW,
                submit_time=1234567890.0
            )
            
            # 提交高优先级任务
            high_task = Task(
                task_id="high_task",
                file_path=temp_file,
                user_id="user2",
                team_id="team2",
                priority=Priority.HIGH,
                submit_time=1234567891.0  # 稍晚提交但优先级更高
            )
            
            self.queue.submit_task(low_task)
            self.queue.submit_task(high_task)
            
            # 高优先级任务应先被处理（尽管稍晚提交）
            processed_first = self.queue.process_next_task(mock_processor)
            self.assertTrue(processed_first)
            
            first_result = self.queue.get_task_result("high_task")
            self.assertEqual(first_result, "Priority: HIGH")
        finally:
            os.unlink(temp_file)


class TestFormatRouter(unittest.TestCase):
    """测试格式路由器功能"""
    
    def test_full_routing_process(self):
        """测试完整的路由过程"""
        def mock_parser(file_path, user_id, team_id, config):
            return {"parsed": True, "strategy": config.strategy.value}
        
        router = FormatRouter(max_workers=2)
        router.register_parser(['text/plain'], mock_parser)
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test content for routing')
            temp_file = f.name
        
        try:
            # 提交文件
            task_id = router.submit_file(temp_file, "user123", "team456", Priority.NORMAL)
            
            # 简单等待处理
            import time
            time.sleep(0.2)
            
            # 检查结果
            result = router.get_task_result(task_id)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)
            # 检查包装结果中的实际解析结果
            parsed_result = result["result"]  # result 包含在包装对象中
            self.assertTrue(parsed_result["parsed"])
        finally:
            os.unlink(temp_file)
    
    def test_router_status(self):
        """测试路由器状态"""
        router = FormatRouter(max_workers=1)
        
        status = router.get_queue_status()
        self.assertIn("pending_tasks", status)
        self.assertIn("running_tasks", status)
        self.assertIn("completed_tasks", status)


if __name__ == '__main__':
    unittest.main()