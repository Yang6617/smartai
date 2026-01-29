"""
任务队列和负载均衡模块

管理解析任务的优先级队列和负载均衡
"""
import heapq
import threading
import time
from collections import deque
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from queue import PriorityQueue
import concurrent.futures
from threading import Lock


class Priority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """任务类"""
    task_id: str
    file_path: str
    user_id: str
    team_id: str
    priority: Priority
    submit_time: float
    callback: Optional[Callable] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __lt__(self, other):
        """优先级队列比较方法，数字越大优先级越高"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # 如果优先级相同，按提交时间排序（早提交的优先）
        return self.submit_time < other.submit_time


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.current_load = 0
        self.lock = Lock()
        self.workers_status = {}  # worker_id -> status
        self.worker_tasks = {}    # worker_id -> task_count
        self._initialize_workers()
    
    def _initialize_workers(self):
        """初始化工作线程状态"""
        for i in range(self.max_workers):
            worker_id = f"worker_{i}"
            self.workers_status[worker_id] = "idle"
            self.worker_tasks[worker_id] = 0
    
    def get_best_worker(self) -> str:
        """获取最佳工作线程"""
        with self.lock:
            # 查找空闲的工作线程
            for worker_id, status in self.workers_status.items():
                if status == "idle":
                    self.workers_status[worker_id] = "busy"
                    self.worker_tasks[worker_id] += 1
                    return worker_id
            
            # 如果没有完全空闲的线程，选择任务最少的
            min_task_worker = min(self.worker_tasks.keys(), 
                                key=lambda k: self.worker_tasks[k])
            self.workers_status[min_task_worker] = "busy"
            self.worker_tasks[min_task_worker] += 1
            return min_task_worker
    
    def release_worker(self, worker_id: str):
        """释放工作线程"""
        with self.lock:
            if worker_id in self.workers_status:
                self.workers_status[worker_id] = "idle"
                if self.worker_tasks[worker_id] > 0:
                    self.worker_tasks[worker_id] -= 1


class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self, max_workers: int = 4):
        self.task_queue = PriorityQueue()
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.running_tasks = {}
        self.load_balancer = LoadBalancer(max_workers)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.lock = Lock()
        self.shutdown_flag = False
    
    def submit_task(self, task: Task) -> str:
        """提交任务到队列"""
        if self.shutdown_flag:
            raise RuntimeError("TaskQueue is shutting down")
        
        self.task_queue.put((-task.priority.value, task.submit_time, task))
        return task.task_id
    
    def process_next_task(self, task_processor: Callable[[Task], Any]) -> bool:
        """处理下一个任务"""
        try:
            # 获取下一个任务
            _, _, task = self.task_queue.get_nowait()
        except:
            # 队列为空
            return False
        
        with self.lock:
            self.running_tasks[task.task_id] = task
        
        # 选择最佳工作线程
        worker_id = self.load_balancer.get_best_worker()
        
        try:
            # 执行任务
            result = task_processor(task)
            
            # 记录完成的任务
            with self.lock:
                del self.running_tasks[task.task_id]
                self.completed_tasks[task.task_id] = result
            
            # 释放工作线程
            self.load_balancer.release_worker(worker_id)
            
            # 执行回调
            if task.callback:
                try:
                    task.callback(task.task_id, result, "success")
                except Exception as e:
                    print(f"Callback execution failed: {e}")
            
            return True
            
        except Exception as e:
            # 记录失败的任务
            with self.lock:
                del self.running_tasks[task.task_id]
                self.failed_tasks[task.task_id] = str(e)
            
            # 释放工作线程
            self.load_balancer.release_worker(worker_id)
            
            # 执行回调
            if task.callback:
                try:
                    task.callback(task.task_id, str(e), "failed")
                except Exception as callback_error:
                    print(f"Callback execution failed: {callback_error}")
            
            return True
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "pending_tasks": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "workers_status": self.load_balancer.workers_status.copy(),
            "worker_tasks": self.load_balancer.worker_tasks.copy()
        }
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """获取任务结果"""
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        elif task_id in self.failed_tasks:
            return self.failed_tasks[task_id]
        elif task_id in self.running_tasks:
            return "running"
        else:
            return None
    
    def shutdown(self):
        """关闭任务队列"""
        self.shutdown_flag = True
        self.executor.shutdown(wait=True)


# 简单测试
if __name__ == "__main__":
    import tempfile
    
    # 创建测试文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'Test file content')
        test_file = f.name
    
    try:
        def dummy_processor(task):
            """模拟任务处理器"""
            time.sleep(0.1)  # 模拟处理时间
            return f"Processed {task.file_path}"
        
        # 创建任务队列
        queue = TaskQueue(max_workers=2)
        
        # 提交一些测试任务
        task1 = Task(
            task_id="task_1",
            file_path=test_file,
            user_id="user1",
            team_id="team1",
            priority=Priority.NORMAL,
            submit_time=time.time()
        )
        
        task2 = Task(
            task_id="task_2",
            file_path=test_file,
            user_id="user2",
            team_id="team2",
            priority=Priority.HIGH,
            submit_time=time.time()
        )
        
        queue.submit_task(task1)
        queue.submit_task(task2)
        
        print("初始队列状态:")
        print(queue.get_queue_status())
        
        # 处理任务
        print("\n处理任务...")
        while queue.process_next_task(dummy_processor):
            print(f"当前状态: {queue.get_queue_status()}")
        
        print(f"\n任务1结果: {queue.get_task_result('task_1')}")
        print(f"任务2结果: {queue.get_task_result('task_2')}")
        
    finally:
        import os
        os.unlink(test_file)