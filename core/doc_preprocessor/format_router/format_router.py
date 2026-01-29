"""
格式路由器主类

整合文件类型识别、策略选择和任务队列管理功能
"""
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import time
import threading
from .file_type_identifier import FileTypeIdentifier
from .strategy_selector import StrategySelector, ParseConfig
from .task_queue import TaskQueue, Task, Priority


class FormatRouter:
    """格式路由器 - 统一管理文档解析流程"""
    
    def __init__(self, max_workers: int = 4):
        self.file_type_identifier = FileTypeIdentifier()
        self.strategy_selector = StrategySelector()
        self.task_queue = TaskQueue(max_workers=max_workers)
        self.parsers_registry = {}  # 解析器注册表
        
        # 将自身作为任务处理器传递给队列
        self._setup_task_processor()
    
    def _setup_task_processor(self):
        """设置任务处理器"""
        def task_processor(task):
            return self.process_task(task)
        
        # 启动后台任务处理线程
        self._start_background_processing(task_processor)
    
    def _start_background_processing(self, task_processor):
        """启动后台任务处理"""
        import threading
        
        def process_loop():
            while not self.task_queue.shutdown_flag:
                try:
                    # 处理下一个任务
                    has_task = self.task_queue.process_next_task(task_processor)
                    if not has_task:
                        # 如果没有任务，短暂休眠避免CPU占用过高
                        time.sleep(0.01)
                except Exception:
                    # 发生异常时也短暂休眠
                    time.sleep(0.01)
        
        # 启动后台处理线程
        processing_thread = threading.Thread(target=process_loop, daemon=True)
        processing_thread.start()
        
    def register_parser(self, mime_types: list, parser_callable: Callable):
        """注册解析器
        
        Args:
            mime_types: 支持的MIME类型列表
            parser_callable: 解析器可调用对象
        """
        for mime_type in mime_types:
            self.parsers_registry[mime_type] = parser_callable
    
    def identify_and_route(self, file_path: str, user_id: str, team_id: str, 
                          priority: Priority = Priority.NORMAL, 
                          callback: Optional[Callable] = None) -> str:
        """
        识别文件类型并路由到适当的解析器
        
        Args:
            file_path: 文件路径
            user_id: 用户ID
            team_id: 团队ID
            priority: 任务优先级
            callback: 完成回调函数
            
        Returns:
            任务ID
        """
        # 1. 识别文件类型
        mime_type, extension, confidence = self.file_type_identifier.identify_file_type(file_path)
        
        # 2. 选择解析策略
        config = self.strategy_selector.select_strategy(file_path, mime_type)
        
        # 3. 创建任务
        task = Task(
            task_id=f"task_{int(time.time() * 1000000)}",  # 微妙级别的时间戳作为ID
            file_path=file_path,
            user_id=user_id,
            team_id=team_id,
            priority=priority,
            submit_time=time.time(),
            callback=callback,
            metadata={
                "mime_type": mime_type,
                "extension": extension,
                "confidence": confidence,
                "parse_config": config
            }
        )
        
        # 4. 提交任务到队列
        task_id = self.task_queue.submit_task(task)
        
        return task_id
    
    def process_task(self, task: Task) -> Dict[str, Any]:
        """
        处理单个任务
        
        Args:
            task: 任务对象
            
        Returns:
            处理结果
        """
        file_path = task.file_path
        mime_type = task.metadata["mime_type"]
        
        # 查找合适的解析器
        parser = self.parsers_registry.get(mime_type)
        if not parser:
            # 尝试查找通配符匹配（如 image/*）
            for registered_type, registered_parser in self.parsers_registry.items():
                if registered_type.endswith('/*') and mime_type.startswith(registered_type[:-1]):
                    parser = registered_parser
                    break
        
        if not parser:
            raise ValueError(f"No parser registered for MIME type: {mime_type}")
        
        # 执行解析
        config = task.metadata["parse_config"]
        result = parser(file_path, task.user_id, task.team_id, config)
        
        return {
            "task_id": task.task_id,
            "file_path": file_path,
            "mime_type": mime_type,
            "result": result,
            "processing_time": time.time() - task.submit_time,
            "config_used": config
        }
    
    def submit_file(self, file_path: str, user_id: str, team_id: str, 
                   priority: Priority = Priority.NORMAL,
                   callback: Optional[Callable] = None) -> str:
        """
        提交文件进行解析
        
        Args:
            file_path: 文件路径
            user_id: 用户ID
            team_id: 团队ID
            priority: 任务优先级
            callback: 完成回调函数
            
        Returns:
            任务ID
        """
        return self.identify_and_route(file_path, user_id, team_id, priority, callback)
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        return self.task_queue.get_task_result(task_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return self.task_queue.get_queue_status()
    
    def shutdown(self):
        """关闭路由器"""
        self.task_queue.shutdown()


# 使用示例
if __name__ == "__main__":
    import tempfile
    
    def mock_parser(file_path, user_id, team_id, config):
        """模拟解析器"""
        print(f"使用 {config.strategy.value} 策略解析文件: {file_path}")
        time.sleep(0.1)  # 模拟处理时间
        return {"status": "success", "file": file_path, "strategy": config.strategy.value}
    
    # 创建格式路由器
    router = FormatRouter(max_workers=2)
    
    # 注册解析器
    router.register_parser(['text/plain', 'text/markdown'], mock_parser)
    
    # 创建测试文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'Test content for routing')
        test_file = f.name
    
    try:
        # 提交文件解析任务
        task_id = router.submit_file(test_file, "user123", "team456", Priority.HIGH)
        print(f"提交任务: {task_id}")
        
        # 简单等待处理
        time.sleep(0.2)
        
        # 获取结果
        result = router.get_task_result(task_id)
        print(f"任务结果: {result}")
        
        # 显示队列状态
        print(f"队列状态: {router.get_queue_status()}")
        
    finally:
        import os
        os.unlink(test_file)