import httpx
import json
import logging
import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI模型服务配置
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5000")  # 模型服务地址
MODEL_TIMEOUT = float(os.getenv("MODEL_TIMEOUT", "30.0"))  # 模型服务超时时间


async def get_answer_from_model(question: str, context: Optional[str] = None, document_id: Optional[int] = None):
    """
    调用AI模型获取答案
    """
    try:
        async with httpx.AsyncClient(timeout=MODEL_TIMEOUT) as client:
            payload = {
                "question": question,
                "context": context or "",
                "document_id": document_id  # 如果有文档ID，传递给模型服务
            }
            response = await client.post(f"{MODEL_SERVICE_URL}/predict", json=payload)
            
            # 检查HTTP错误
            if response.status_code != 200:
                logger.warning(f"Model service returned status {response.status_code}: {response.text}")
                # 返回一个更友好的消息而不是直接报错
                return f"参考问题: {question}\n\n这是模拟响应，实际模型服务暂不可用。请稍后重试或联系管理员。"
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                logger.warning(f"Model service returned invalid JSON: {response.text}")
                return f"参考问题: {question}\n\n模型服务返回的数据格式错误。这是模拟响应。"
            
            # 检查返回的数据结构
            if "answer" not in result:
                logger.warning(f"Model service response missing 'answer' field: {result}")
                return f"参考问题: {question}\n\n模型服务返回的数据格式错误。这是模拟响应。"
                
            return result.get("answer", "抱歉，我暂时无法回答您的问题。")
    except httpx.TimeoutException:
        logger.warning(f"Model service timeout after {MODEL_TIMEOUT}s")
        # 超时时返回模拟响应而不是抛出异常
        return f"参考问题: {question}\n\n模型服务响应超时，这是模拟响应。请稍后重试。"
    except httpx.RequestError as e:
        logger.error(f"Error calling model service: {e}")
        # 请求错误时返回模拟响应而不是抛出异常
        return f"参考问题: {question}\n\n模型服务暂时不可用，请稍后再试。这是模拟响应。"
    except Exception as e:
        logger.error(f"Unexpected error calling model service: {e}")
        # 其他异常也返回模拟响应
        return f"参考问题: {question}\n\n处理您的问题时发生错误。这是模拟响应。"