"""
格式路由分发模块 - 初始化文件

该模块负责识别文件类型并分发到对应的解析通道
主要功能包括：
1. 通过文件扩展名和二进制签名双重验证文件类型
2. 根据文件大小和类型选择最优解析策略
3. 管理解析任务的优先级队列和负载均衡
"""

from .file_type_identifier import FileTypeIdentifier
from .strategy_selector import StrategySelector, ParseStrategy, ParseConfig
from .task_queue import TaskQueue, Task, Priority
from .format_router import FormatRouter

__all__ = [
    'FileTypeIdentifier',
    'StrategySelector', 
    'ParseStrategy',
    'ParseConfig',
    'TaskQueue',
    'Task',
    'Priority',
    'FormatRouter'
]