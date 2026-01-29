from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PromptType(str, Enum):
    """
    Prompt 类型（与意图大致对应）
    """
    FACT_QA = "fact_qa"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    HOWTO = "howto"
    EXPLAIN = "explain"
    DEFAULT = "default"


@dataclass
class PromptTemplate:
    """
    Prompt 模板定义
    """
    system_prompt: str
    user_prompt: str


# ===== 默认模板库 =====

DEFAULT_TEMPLATES = {
    PromptType.FACT_QA: PromptTemplate(
        system_prompt=(
            "你是一个严谨的知识库问答助手。"
            "只能基于给定的参考资料回答问题。"
            "如果资料不足，请明确说明无法回答。"
        ),
        user_prompt=(
            "问题：{question}\n\n"
            "参考资料：\n{context}\n\n"
            "请基于以上资料回答，并在回答中标注引用编号。"
        ),
    ),
    PromptType.SUMMARIZE: PromptTemplate(
        system_prompt="你是一个文档总结助手，擅长提炼关键信息。",
        user_prompt=(
            "请对以下资料进行总结：\n\n"
            "{context}\n\n"
            "总结要求：条理清晰、简洁准确。"
        ),
    ),
    PromptType.COMPARE: PromptTemplate(
        system_prompt="你是一个分析对比助手。",
        user_prompt=(
            "请基于以下资料，对问题进行对比分析：\n\n"
            "问题：{question}\n\n"
            "资料：\n{context}"
        ),
    ),
    PromptType.DEFAULT: PromptTemplate(
        system_prompt="你是一个知识型助手。",
        user_prompt=(
            "问题：{question}\n\n"
            "参考资料：\n{context}"
        ),
    ),
}
