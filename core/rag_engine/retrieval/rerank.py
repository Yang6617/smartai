from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import re

from core.rag_engine.retrieval.vector_retriever import RetrievalHit


@dataclass
class RerankConfig:
    enabled: bool = True  # 默认启用重排
    top_k: int = 8


class Reranker:
    """
    重排器
    
    实现基于标题层级的重排策略：
    - 优先选择来自更具体标题层级（如'3. 主要技术分支'）的内容
    - 避免仅依赖过于宽泛的标题（如'1. 引言'）
    """

    def __init__(self, config: Optional[RerankConfig] = None) -> None:
        self.config = config or RerankConfig()

    def rerank(self, query: str, hits: List[RetrievalHit]) -> List[RetrievalHit]:
        """
        根据标题层级和向量相似度重新排序
        """
        if not self.config.enabled:
            return hits[: self.config.top_k]
        
        # 调试信息：打印重排前的hits
        print(f"[Reranker] 重排前的hits数量: {len(hits)}")
        for i, hit in enumerate(hits):
            print(f"  Hit {i}: score={hit.score:.4f}, source_info={hit.source_info}, text_preview={hit.text[:50]}...")
        
        def get_title_level(source_info: str) -> int:
            """
            获取标题层级深度
            例如：'1. 引言' -> 1级，'3. 主要技术分支' -> 1级，'3.1 机器学习' -> 2级
            """
            if not source_info:
                return 0
            # 统计' > '的数量，+1得到层级深度
            level = source_info.count(' > ') + 1
            return level
        
        def is_specific_topic(source_info: str, text: str = "") -> bool:
            """
            判断是否为具体主题（而非宽泛主题）
            例如：'3. 主要技术分支' 是具体主题，'1. 引言' 是宽泛主题
            """
            if not source_info:
                # 如果source_info为空，从text中推断
                if not text:
                    return False
                # 检查是否包含数字编号的标题（如'3. 主要技术分支'）
                if re.search(r'\d+\.\s+\S+', text):
                    return True
                # 检查是否包含时间关键词（如'1956年'、'1960年代'等）
                if re.search(r'\d{4}年', text):
                    return True
                # 检查是否包含具体技术分支关键词
                specific_keywords = ['机器学习', '深度学习', '计算机视觉', '自然语言处理', '机器人', '语音识别', '图像识别', '专家系统']
                if any(keyword in text for keyword in specific_keywords):
                    return True
                return False
            # 检查是否包含数字编号的标题（如'3. 主要技术分支'）
            if re.search(r'\d+\.\s+\S+', source_info):
                return True
            # 检查text中是否包含时间关键词
            if text and re.search(r'\d{4}年', text):
                return True
            return False
        
        def get_tech_branch_score(text: str) -> int:
            """
            计算技术分支相关性分数
            例如：包含'机器学习'、'深度学习'等关键词的text分数更高
            """
            if not text:
                return 0
            tech_keywords = ['机器学习', '深度学习', '计算机视觉', '自然语言处理', '机器人', '语音识别', '图像识别', '专家系统']
            score = sum(1 for keyword in tech_keywords if keyword in text)
            return score
        
        def get_title_level_from_text(text: str) -> int:
            """
            从text内容中推断标题层级
            例如：包含'3. 主要技术分支' -> 1级，'3.1 机器学习' -> 2级
            """
            # 检查是否包含标题编号
            if re.search(r'^#+\s+', text):
                # Markdown标题格式
                matches = re.findall(r'^(#+)\s+', text, re.MULTILINE)
                if matches:
                    # 返回最长的#数量
                    return max(len(m) for m in matches)
            elif re.search(r'\d+\.\s+\S+', text):
                # 编号标题格式（如'3. 主要技术分支'）
                return 1
            elif re.search(r'\d+\.\d+\s+', text):
                # 多级编号标题（如'3.1 机器学习'）
                return 2
            return 0
        
        def get_position_score(hit: RetrievalHit, query: str) -> float:
            """
            根据位置信息计算分数
            对于时间相关查询（如"发展历程"），优先选择位置靠上的结果
            对于技术相关查询（如"技术分支"），优先选择位置靠下的结果
            """
            if not hit.y_top:
                return 0.5  # 没有位置信息时返回中等分数
            
            # 检测查询类型
            is_temporal = any(keyword in query for keyword in ['发展', '历程', '历史', '年代', '时间', '阶段'])
            is_tech = any(keyword in query for keyword in ['技术', '分支', '机器学习', '深度学习', '计算机视觉', '自然语言处理'])
            
            # 归一化y坐标（假设y_top范围在0-1500之间）
            normalized_y = min(hit.y_top / 1500.0, 1.0)
            
            if is_temporal:
                # 时间相关查询：优先选择位置靠上的结果（y_top较小）
                return 1.0 - normalized_y
            elif is_tech:
                # 技术相关查询：优先选择位置靠下的结果（y_top较大）
                return normalized_y
            else:
                # 默认：位置靠上的结果优先
                return 1.0 - normalized_y
        
        # 重新排序：先按位置信息排序，再按其他因素排序
        def get_sort_key(x):
            is_spec = is_specific_topic(x.source_info or '', x.text or '')
            title_level = -max(get_title_level(x.source_info or ''), get_title_level_from_text(x.text or ''))
            tech_score = -get_tech_branch_score(x.text or '')
            position_score = get_position_score(x, query)
            # 优先级调整：位置信息优先级最高，其次是具体主题、层级深度、技术分支相关性
            # 注意：sorted默认从小到大排序，所以position_score需要取负以实现从大到小排序
            key = (-position_score, not is_spec, title_level, tech_score)
            return key
        
        # 调试信息：打印排序键
        print("\n[Reranker] 排序键:")
        for i, hit in enumerate(hits):
            key = get_sort_key(hit)
            position_score = get_position_score(hit, query)
            print(f"  Hit {i}: y_top={hit.y_top}, position_score={position_score:.3f}, key={key}")
        
        hits_sorted = sorted(hits, key=get_sort_key)
        
        return hits_sorted[: self.config.top_k]
