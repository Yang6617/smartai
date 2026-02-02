from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class QueryExpansionResult:
    """查询扩展结果"""
    expanded_query: str
    original_query: str
    expansion_terms: List[str]
    confidence: float


class QueryExpander:
    """
    查询扩展器 - 用于增强简短或模糊的用户查询
    """
    
    def __init__(self):
        # 扩展词典：将简短查询扩展为更具体的查询
        self.expansion_rules: Dict[str, List[str]] = {
            # 技术相关
            "前端": ["前端技术", "前端开发", "前端框架", "前端架构"],
            "后端": ["后端技术", "后端开发", "后端架构", "后端框架"],
            "API": ["API接口", "API设计", "API规范", "应用程序编程接口"],
            "数据库": ["数据库系统", "数据库技术", "数据存储", "数据库架构"],
            "架构": ["系统架构", "软件架构", "技术架构", "架构设计"],
            "模型": ["AI模型", "机器学习模型", "深度学习模型", "模型部署"],
            
            # 操作相关
            "上传": ["如何上传", "上传方法", "上传步骤", "上传操作"],
            "下载": ["如何下载", "下载方法", "下载步骤", "下载操作"],
            "配置": ["如何配置", "配置方法", "配置步骤", "配置操作"],
            "部署": ["如何部署", "部署方法", "部署步骤", "部署操作"],
            
            # 问题解决相关
            "解决": ["如何解决", "解决方法", "解决方案", "问题解决"],
            "修复": ["如何修复", "修复方法", "修复步骤", "问题修复"],
            "处理": ["如何处理", "处理方法", "处理步骤", "问题处理"],
            
            # 定义相关
            "定义": ["XX的定义", "XX是什么", "XX的意思", "XX的含义"],
            "意思": ["XX的意思", "XX的含义", "XX的解释", "XX是什么"],
            "含义": ["XX的含义", "XX的意思", "XX的解释", "XX是什么"],
            "解释": ["XX的解释", "XX是什么", "XX的意思", "XX的含义"],
        }
        
        # 常见缩写扩展
        self.abbreviation_expansions: Dict[str, str] = {
            "API": "应用程序编程接口",
            "JWT": "JSON Web Token",
            "ORM": "对象关系映射",
            "RAG": "检索增强生成",
            "LLM": "大型语言模型",
            "QA": "问答系统",
        }

    def expand_query(self, query: str) -> QueryExpansionResult:
        """
        扩展查询
        """
        original_query = query.strip()
        if not original_query:
            return QueryExpansionResult(
                expanded_query=original_query,
                original_query=original_query,
                expansion_terms=[],
                confidence=0.0
            )
        
        expanded_terms = []
        expansion_terms = []
        
        # 检查是否有缩写需要扩展
        for abbr, full_form in self.abbreviation_expansions.items():
            if abbr in original_query:
                expanded_query = original_query.replace(abbr, full_form)
                expansion_terms.append(f"{abbr} -> {full_form}")
                break
        else:
            expanded_query = original_query
        
        # 检查是否需要使用扩展规则
        query_lower = expanded_query.lower()
        for keyword, expansions in self.expansion_rules.items():
            if keyword.lower() in query_lower:
                # 找到最佳匹配的扩展
                best_expansion = expansions[0] if expansions else keyword
                # 将XX替换为实际查询内容
                actual_query = expanded_query.replace(keyword, "XX")
                best_expansion = best_expansion.replace("XX", actual_query)
                
                if best_expansion != expanded_query:
                    expanded_terms.append(best_expansion)
                    expansion_terms.append(f"'{keyword}' -> '{best_expansion}'")
        
        # 如果原查询很短且没有找到扩展，尝试基于关键词扩展
        if len(original_query) <= 10 and not expanded_terms:
            # 基于查询中包含的关键字进行扩展
            if any(char in original_query for char in "什么是什么意思含义解释"):
                expanded_terms.append(f"{original_query}的相关定义")
                expanded_terms.append(f"{original_query}的具体含义")
                expansion_terms.append("添加定义查询")
            elif any(char in original_query for char in "如何怎样怎么操作步骤"):
                expanded_terms.append(f"关于{original_query}的操作方法")
                expanded_terms.append(f"{original_query}的实现步骤")
                expansion_terms.append("添加操作查询")
            elif "?" in original_query or "？" in original_query:
                # 已经是疑问句，不需要太多扩展
                pass
            else:
                # 添加一些常见的查询后缀
                expanded_terms.extend([
                    f"{original_query}是什么",
                    f"{original_query}有什么",
                    f"{original_query}如何",
                    f"{original_query}的作用"
                ])
                expansion_terms.append("添加常见查询变体")
        
        # 合并原始查询和扩展项
        if expanded_terms:
            final_expanded = f"{expanded_query} " + " ".join(expanded_terms)
        else:
            final_expanded = expanded_query
        
        # 计算置信度：基于扩展程度
        confidence = min(0.9, 0.3 + len(expansion_terms) * 0.2)
        
        return QueryExpansionResult(
            expanded_query=final_expanded.strip(),
            original_query=original_query,
            expansion_terms=expansion_terms,
            confidence=confidence
        )


# 全局查询扩展器实例
query_expander = QueryExpander()