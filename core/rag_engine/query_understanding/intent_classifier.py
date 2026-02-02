from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


class QueryIntent(str, Enum):
    """
    查询意图枚举（粗粒度）

    用于控制 RAG 后续行为策略（检索方式、prompt 模板等）
    """
    FACT_QA = "fact_qa"                 # 事实问答（明确问题，精确检索）
    SUMMARIZE = "summarize"             # 总结概括
    COMPARE = "compare"                 # 对比分析
    HOWTO = "howto"                     # 操作步骤 / 指引
    TROUBLESHOOT = "troubleshoot"       # 故障排查 / 报错解决
    EXPLAIN = "explain"                 # 原理解释 / 背景说明
    DEFINITION = "definition"           # 术语定义
    LIST = "list"                       # 列表 / 枚举
    SMALLTALK = "smalltalk"             # 闲聊 / 非知识库问题
    UNKNOWN = "unknown"                 # 无法判断


@dataclass
class IntentResult:
    """
    意图识别结果
    """
    intent: QueryIntent                # 识别出的意图
    confidence: float                  # 置信度（0~1）
    signals: Dict[str, float]           # 触发信号与得分（调试用）
    rationale: str                      # 判定原因说明
    language: str                       # 查询语言（zh / en / mixed）


class IntentClassifier:
    """
    查询意图识别器（基于规则与关键词）

    设计目标：
    - 无外部依赖
    - 行为确定、可解释
    - 方便后续替换为 ML / LLM 模型
    """

    def __init__(self) -> None:
        # 意图 → [(关键词列表, 权重)]
        self._patterns: Dict[QueryIntent, List[Tuple[List[str], float]]] = {
            QueryIntent.SUMMARIZE: [
                (["总结", "概括", "梳理", "提炼", "总结一下"], 2.0),
                (["summary", "summarize", "overview", "tl;dr"], 2.0),
            ],
            QueryIntent.COMPARE: [
                (["对比", "比较", "差异", "区别", "哪个好", "优缺点"], 2.0),
                (["compare", "difference", "vs", "versus"], 2.0),
            ],
            QueryIntent.HOWTO: [
                (["怎么做", "如何", "步骤", "流程", "实现", "部署", "配置"], 1.8),
                (["how to", "steps", "guide", "setup"], 1.8),
            ],
            QueryIntent.TROUBLESHOOT: [
                (["报错", "错误", "异常", "失败", "无法", "怎么解决"], 2.2),
                (["error", "exception", "failed", "doesn't work"], 2.2),
            ],
            QueryIntent.DEFINITION: [
                (["是什么", "定义", "含义"], 1.6),
                (["what is", "define", "definition"], 1.6),
            ],
            QueryIntent.EXPLAIN: [
                (["为什么", "原理", "机制", "怎么回事"], 1.5),
                (["why", "how it works", "principle"], 1.5),
            ],
            QueryIntent.LIST: [
                (["列出", "有哪些", "列表", "清单"], 1.3),
                (["list", "items", "what are"], 1.3),
            ],
            QueryIntent.FACT_QA: [
                (["多少", "谁", "哪里", "何时", "哪个"], 1.0),
                (["what", "when", "where", "who", "which"], 1.0),
            ],
            QueryIntent.SMALLTALK: [
                (["你好", "在吗", "哈哈", "谢谢"], 1.0),
                (["hello", "hi", "thanks"], 1.0),
            ],
        }

    def classify(self, query: str) -> IntentResult:
        """
        对查询进行意图识别
        """
        q = (query or "").strip()
        if not q:
            return IntentResult(
                intent=QueryIntent.UNKNOWN,
                confidence=0.0,
                signals={},
                rationale="空查询",
                language="unknown",
            )

        language = self._detect_language(q)
        scores = {intent: 0.0 for intent in QueryIntent}

        # 关键词规则打分
        for intent, patterns in self._patterns.items():
            for keywords, weight in patterns:
                for kw in keywords:
                    if kw.lower() in q.lower():
                        scores[intent] += weight

        # 简单启发式规则
        if len(q) <= 10:
            scores[QueryIntent.FACT_QA] += 0.4
        if "?" in q or "？" in q:
            scores[QueryIntent.FACT_QA] += 0.3

        # 如果没有任何关键词匹配，但查询长度适中，考虑为FACT_QA
        total_score = sum(scores.values())
        if total_score == 0:
            # 使用更宽松的判断标准，防止所有查询都被标记为UNKNOWN
            if any(word in q.lower() for word in ["什么", "怎么", "如何", "哪个", "哪个", "what", "how", "where", "when", "why"]):
                scores[QueryIntent.FACT_QA] = 0.5
            elif len(q) > 5:
                scores[QueryIntent.FACT_QA] = 0.3
            else:
                scores[QueryIntent.UNKNOWN] = 0.5

        # 为简短查询增加额外的处理逻辑
        if len(q) <= 5:
            # 对于非常简短的查询，根据字符类型给予不同权重
            if any(c.isdigit() for c in q):
                scores[QueryIntent.FACT_QA] += 0.2
            if any(c in "什么哪谁哪里怎么如何为何" for c in q):
                scores[QueryIntent.FACT_QA] += 0.3
            if any(c in "定义解释意思含义" for c in q):
                scores[QueryIntent.DEFINITION] += 0.3
            if any(c in "列表列举都有哪些" for c in q):
                scores[QueryIntent.LIST] += 0.3
            if any(c in "怎么做如何操作步骤流程" for c in q):
                scores[QueryIntent.HOWTO] += 0.3

        # 选取得分最高的意图
        best_intent, best_score = max(scores.items(), key=lambda x: x[1])
        
        # 计算置信度，确保即使分数较低也返回一个合理的意图
        confidence = min(1.0, max(0.2, best_score / 2.0))  # 最低置信度0.2
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        signals = {k.value: v for k, v in top3 if v > 0}

        rationale = f"意图={best_intent.value}, 得分={best_score:.2f}"
        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            signals=signals,
            rationale=rationale,
            language=language,
        )

    @staticmethod
    def _detect_language(text: str) -> str:
        """
        简单语言识别（中/英/混合）
        """
        has_zh = any("\u4e00" <= c <= "\u9fff" for c in text)
        has_en = any("a" <= c.lower() <= "z" for c in text)
        if has_zh and has_en:
            return "mixed"
        if has_zh:
            return "zh"
        if has_en:
            return "en"
        return "unknown"
