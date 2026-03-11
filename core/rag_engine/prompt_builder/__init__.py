"""
Prompt Builder 模块

负责：
- Prompt 模板管理
- 将检索结果组装为 LLM 可用上下文
- 引用标注与安全约束
"""

from core.rag_engine.prompt_builder.templates import PromptTemplate, PromptType,DEFAULT_TEMPLATES
from core.rag_engine.prompt_builder.assembler import PromptAssembler, AssembledPrompt
from core.rag_engine.prompt_builder.safety import SafetyGuard

__all__ = [
    "PromptTemplate",
    "PromptType",
    "PromptAssembler",
    "AssembledPrompt",
    "SafetyGuard",
    "DEFAULT_TEMPLATES",
]
