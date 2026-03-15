"""
格式路由分发模块使用示例
"""
from core.doc_preprocessor.format_router import FormatRouter, Priority
import tempfile
import os


def mock_text_parser(file_path, user_id, team_id, config):
    """模拟文本解析器"""
    print(f"[{config.strategy.value}] 解析文本文件: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 模拟解析过程
    elements = [{"type": "paragraph", "content": content}]
    
    return {
        "user_id": user_id,
        "team_id": team_id,
        "file_path": file_path,
        "elements": elements,
        "strategy_used": config.strategy.value
    }


def mock_pdf_parser(file_path, user_id, team_id, config):
    """模拟PDF解析器"""
    print(f"[{config.strategy.value}] 解析PDF文件: {file_path}")
    
    # 模拟PDF解析过程
    elements = [{"type": "page", "content": f"PDF content from {os.path.basename(file_path)}"}]
    
    return {
        "user_id": user_id,
        "team_id": team_id,
        "file_path": file_path,
        "elements": elements,
        "strategy_used": config.strategy.value
    }


def mock_image_parser(file_path, user_id, team_id, config):
    """模拟图像解析器（OCR）"""
    print(f"[{config.strategy.value}] 解析图像文件（OCR）: {file_path}")
    
    # 模拟OCR过程
    elements = [{"type": "ocr_text", "content": f"Text extracted from {os.path.basename(file_path)}"}]
    
    return {
        "user_id": user_id,
        "team_id": team_id,
        "file_path": file_path,
        "elements": elements,
        "strategy_used": config.strategy.value
    }


def demo_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("1. 基本使用示例")
    print("=" * 60)
    
    # 创建格式路由器
    router = FormatRouter(max_workers=4)
    
    # 注册不同类型的解析器
    router.register_parser(['text/plain', 'text/markdown'], mock_text_parser)
    router.register_parser(['application/pdf'], mock_pdf_parser)
    router.register_parser(['image/jpeg', 'image/png'], mock_image_parser)
    
    print("✓ 解析器注册成功")
    print(f"✓ 支持的格式: {list(router.parsers_registry.keys())}")
    
    # 创建测试文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
        f.write("这是一个测试文档。\n包含多行内容。\n用于演示格式路由功能。")
        txt_file = f.name
    
    try:
        # 提交文件解析任务
        print(f"\n提交文本文件解析任务: {os.path.basename(txt_file)}")
        task_id = router.submit_file(txt_file, "user_123", "team_abc", Priority.NORMAL)
        print(f"任务ID: {task_id}")
        
        # 等待处理完成
        import time
        time.sleep(0.2)
        
        # 获取结果
        result = router.get_task_result(task_id)
        if result and result != "running":
            # result 是包装后的结果，实际解析结果在 result['result'] 中
            actual_result = result['result']
            print(f"✓ 解析完成: {actual_result['strategy_used']} 策略")
            print(f"  元素数量: {len(actual_result['elements'])}")
        else:
            print("⚠ 任务仍在运行中")
        
        # 显示队列状态
        status = router.get_queue_status()
        print(f"\n队列状态: {status}")
        
    finally:
        os.unlink(txt_file)


def demo_priority_handling():
    """优先级处理示例"""
    print("\n" + "=" * 60)
    print("2. 优先级处理示例")
    print("=" * 60)
    
    router = FormatRouter(max_workers=2)
    router.register_parser(['text/plain'], mock_text_parser)
    
    # 创建多个测试文件
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
            f.write(f"测试文件 {i+1} 的内容")
            temp_files.append(f.name)
    
    try:
        # 提交不同优先级的任务
        task_ids = []
        
        # 低优先级任务
        task_id_low = router.submit_file(temp_files[0], "user_low", "team_low", Priority.LOW)
        task_ids.append(("LOW", task_id_low))
        print(f"提交低优先级任务: {task_id_low}")
        
        # 高优先级任务
        task_id_high = router.submit_file(temp_files[1], "user_high", "team_high", Priority.HIGH)
        task_ids.append(("HIGH", task_id_high))
        print(f"提交高优先级任务: {task_id_high}")
        
        # 紧急优先级任务
        task_id_urgent = router.submit_file(temp_files[2], "user_urgent", "team_urgent", Priority.URGENT)
        task_ids.append(("URGENT", task_id_urgent))
        print(f"提交紧急优先级任务: {task_id_urgent}")
        
        # 处理所有任务
        import time
        time.sleep(0.3)
        
        # 检查结果顺序（理论上紧急任务最先完成）
        for priority, task_id in task_ids:
            result = router.get_task_result(task_id)
            if result and result != "running":
                # result 是包装后的结果，实际解析结果在 result['result'] 中
                actual_result = result['result']
                print(f"✓ {priority} 优先级任务 {task_id} 完成: {actual_result['strategy_used']}")
            else:
                print(f"⚠ {priority} 优先级任务 {task_id} 仍在运行")
        
    finally:
        for file_path in temp_files:
            os.unlink(file_path)


def demo_file_type_detection():
    """文件类型检测示例"""
    print("\n" + "=" * 60)
    print("3. 文件类型检测示例")
    print("=" * 60)
    
    from core.doc_preprocessor.format_router import FileTypeIdentifier, StrategySelector
    
    identifier = FileTypeIdentifier()
    selector = StrategySelector()
    
    # 创建不同类型的测试文件
    test_files = []
    
    # TXT文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
        f.write("这是纯文本内容")
        test_files.append(("TXT", f.name))
    
    # PDF文件（模拟）
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='wb') as f:
        f.write(b'%PDF-1.4\n')  # PDF文件头
        test_files.append(("PDF", f.name))
    
    try:
        for file_type, file_path in test_files:
            print(f"\n分析 {file_type} 文件: {os.path.basename(file_path)}")
            
            # 识别文件类型
            mime_type, ext, confidence = identifier.identify_file_type(file_path)
            print(f"  MIME类型: {mime_type}")
            print(f"  扩展名: {ext}")
            print(f"  置信度: {confidence:.2f}")
            
            # 选择解析策略
            config = selector.select_strategy(file_path, mime_type)
            print(f"  选择策略: {config.strategy.value}")
            print(f"  块大小: {config.chunk_size}")
            print(f"  超时: {config.timeout}s")
    
    finally:
        for _, file_path in test_files:
            os.unlink(file_path)


def demo_load_balancing():
    """负载均衡示例"""
    print("\n" + "=" * 60)
    print("4. 负载均衡示例")
    print("=" * 60)
    
    router = FormatRouter(max_workers=3)
    router.register_parser(['text/plain'], mock_text_parser)
    
    # 创建多个测试文件
    temp_files = []
    for i in range(5):
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w', encoding='utf-8') as f:
            f.write(f"负载均衡测试文件 {i+1}\n包含一些内容用于处理")
            temp_files.append(f.name)
    
    try:
        # 同时提交多个任务
        task_ids = []
        for i, file_path in enumerate(temp_files):
            task_id = router.submit_file(file_path, f"user_{i}", f"team_{i}", Priority.NORMAL)
            task_ids.append(task_id)
            print(f"提交任务 {i+1}: {task_id}")
        
        # 等待处理
        import time
        time.sleep(0.5)
        
        # 检查队列状态
        status = router.get_queue_status()
        print(f"\n最终队列状态:")
        print(f"  待处理任务: {status['pending_tasks']}")
        print(f"  运行中任务: {status['running_tasks']}")
        print(f"  完成任务: {status['completed_tasks']}")
        print(f"  失败任务: {status['failed_tasks']}")
        print(f"  工作线程状态: {status['workers_status']}")
        print(f"  工作线程任务数: {status['worker_tasks']}")
        
        # 检查所有任务结果
        completed = 0
        for task_id in task_ids:
            result = router.get_task_result(task_id)
            if result and result != "running":
                completed += 1
        
        print(f"\n总共完成任务: {completed}/{len(task_ids)}")
        
    finally:
        for file_path in temp_files:
            os.unlink(file_path)


def main():
    """主函数 - 运行所有示例"""
    print("格式路由分发模块使用示例")
    print("功能包括：文件类型识别、策略选择、任务队列管理和负载均衡")
    
    demo_basic_usage()
    demo_priority_handling()
    demo_file_type_detection()
    demo_load_balancing()
    
    print("\n" + "=" * 60)
    print("格式路由分发模块演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()