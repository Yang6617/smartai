"""
Prompt Builder 模块

负责：
- Prompt 模板管理
- 将检索结果组装为 LLM 可用上下文
- 引用标注与安全约束
"""

from .templates import PromptTemplate, PromptType,DEFAULT_TEMPLATES
from .assembler import PromptAssembler, AssembledPrompt
from .safety import SafetyGuard

__all__ = [
    "PromptTemplate",
    "PromptType",
    "PromptAssembler",
    "AssembledPrompt",
    "SafetyGuard",
    "DEFAULT_TEMPLATES",
]
