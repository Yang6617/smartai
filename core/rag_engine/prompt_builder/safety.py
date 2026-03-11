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
            "【重要引用规则】\n"
            "1. 回答时请在相关句子后标注引用编号，例如：[1]、[2]。\n"
            "2. 【关键规则】如果多个引用编号来自同一个文档（即具有相同的文档ID），且回答的内容都来自该文档，**必须只标注一个最小的引用编号**（例如：[1]），不要重复标注该文档的其他编号。\n"
            "3. 不要编造参考资料。"
        )
