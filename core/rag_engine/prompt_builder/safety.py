class SafetyGuard:
    """
    Prompt 安全约束模块

    功能：
    - 强制引用
    - 防止幻觉（无资料乱答）
    """

    @staticmethod
    def ensure_context_or_refuse(context: str) -> str:
        """
        如果没有任何上下文，要求模型拒答
        """
        if not context.strip():
            return (
                "【注意】当前没有任何可用参考资料。"
                "如果无法从资料中得到答案，请明确回复“资料不足，无法回答该问题”。"
            )
        return ""

    @staticmethod
    def enforce_citation_instruction() -> str:
        """
        强制引用指令
        """
        return (
            "回答时请在相关句子后标注引用编号，例如：[1]、[2]。"
            "只能使用提供的引用编号，不要编造参考资料，不要伪造编号。"
        )

    @staticmethod
    def enforce_answer_style() -> str:
        return (
            "请优先给出简洁结论，再给出依据。"
            "如果只能部分回答，请明确指出哪些内容来自资料，哪些内容资料中未提及。"
            "不要把推测写成确定事实。"
        )