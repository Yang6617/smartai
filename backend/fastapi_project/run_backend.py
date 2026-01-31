"""
启动后端服务的脚本，正确设置Python路径
"""
import sys
import os

# 添加项目根目录到Python路径，确保能导入core模块
current_file_dir = os.path.dirname(os.path.abspath(__file__))  # fastapi_project目录
project_root = os.path.dirname(os.path.dirname(current_file_dir))  # 项目根目录 (ai_model_service)
project_root = os.path.abspath(project_root)  # 确保是绝对路径

if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"项目根目录已添加到Python路径: {project_root}")

# 验证能否导入核心服务接口
try:
    from core.service_interface import ask_question_interface, upload_file_interface
    print("✅ 成功导入核心服务接口")
except ImportError as e:
    print(f"❌ 导入核心服务接口失败: {e}")
    sys.exit(1)

import uvicorn

# 动态导入app，确保使用正确的路径
sys.path.insert(0, os.path.join(current_file_dir))
import main
app = main.app

print("正在启动知识问答系统...")
print("注意：如果没有错误，服务器将在几秒内启动")

try:
    # 尝试使用一个不太常见的端口
    port = 8002
    print(f"服务器将在 http://127.0.0.1:{port} 上启动")
    print(f"API文档: http://127.0.0.1:{port}/docs")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
except KeyboardInterrupt:
    print("服务器启动被用户中断")
except Exception as e:
    print(f"启动服务器时发生错误: {e}")
    import traceback
    traceback.print_exc()