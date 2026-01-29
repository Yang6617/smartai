"""
重叠控制模块
防止分割切断上下文，通过在相邻块之间添加重叠内容
"""
from typing import List, Dict, Any
from abc import ABC, abstractmethod


class OverlapController(ABC):
    """重叠控制器抽象基类"""
    
    @abstractmethod
    def apply_overlap(self, chunks: List[Dict[str, Any]], overlap_size: int = 50) -> List[Dict[str, Any]]:
        """
        对分块结果应用重叠控制
        
        Args:
            chunks: 原始分块结果
            overlap_size: 重叠大小（字符数）
            
        Returns:
            应用重叠后的分块结果
        """
        pass


class SimpleOverlapController(OverlapController):
    """简单重叠控制器"""
    
    def apply_overlap(self, chunks: List[Dict[str, Any]], overlap_size: int = 50) -> List[Dict[str, Any]]:
        """
        简单的重叠控制：将前一个块的末尾部分添加到下一个块的开头
        
        Args:
            chunks: 原始分块结果
            overlap_size: 重叠大小（字符数）
            
        Returns:
            应用重叠后的分块结果
        """
        if not chunks or len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            new_chunk = chunk.copy()
            
            # 对于第一个块，不需要前置重叠
            if i == 0:
                new_chunk["overlap_prefix"] = ""
                new_chunk["overlap_suffix"] = ""
            else:
                # 获取前一个块的后overlap_size个字符作为重叠前缀
                prev_chunk_text = chunks[i-1]["text"]
                overlap_prefix = prev_chunk_text[-overlap_size:] if len(prev_chunk_text) >= overlap_size else prev_chunk_text
                new_chunk["overlap_prefix"] = overlap_prefix
                
                # 设置后缀（下一个块的前overlap_size个字符，如果存在的话）
                overlap_suffix = ""
                if i < len(chunks) - 1:
                    next_chunk_text = chunks[i+1]["text"]
                    overlap_suffix = next_chunk_text[:overlap_size] if len(next_chunk_text) >= overlap_size else next_chunk_text
                new_chunk["overlap_suffix"] = overlap_suffix
            
            # 构建带有重叠的文本
            overlapped_text = new_chunk["overlap_prefix"] + new_chunk["text"]
            new_chunk["text_with_overlap"] = overlapped_text
            new_chunk["original_text"] = new_chunk["text"]
            
            overlapped_chunks.append(new_chunk)
        
        return overlapped_chunks


class SemanticOverlapController(OverlapController):
    """语义重叠控制器"""
    
    def apply_overlap(self, chunks: List[Dict[str, Any]], overlap_size: int = 50) -> List[Dict[str, Any]]:
        """
        语义重叠控制：尝试在有意义的边界处进行重叠，而不是简单的字符截取
        
        Args:
            chunks: 原始分块结果
            overlap_size: 重叠大小（字符数）
            
        Returns:
            应用重叠后的分块结果
        """
        if not chunks or len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            new_chunk = chunk.copy()
            
            if i == 0:
                new_chunk["overlap_prefix"] = ""
                new_chunk["overlap_suffix"] = ""
            else:
                # 尝试在句子或单词边界处进行重叠
                prev_chunk_text = chunks[i-1]["text"]
                overlap_prefix = self._get_semantic_overlap(prev_chunk_text, overlap_size)
                new_chunk["overlap_prefix"] = overlap_prefix
                
                # 设置后缀
                overlap_suffix = ""
                if i < len(chunks) - 1:
                    next_chunk_text = chunks[i+1]["text"]
                    overlap_suffix = self._get_semantic_overlap(next_chunk_text, overlap_size, prefix=False)
                new_chunk["overlap_suffix"] = overlap_suffix
            
            # 构建带有重叠的文本
            overlapped_text = new_chunk["overlap_prefix"] + new_chunk["text"]
            new_chunk["text_with_overlap"] = overlapped_text
            new_chunk["original_text"] = new_chunk["text"]
            
            overlapped_chunks.append(new_chunk)
        
        return overlapped_chunks
    
    def _get_semantic_overlap(self, text: str, overlap_size: int, prefix: bool = True) -> str:
        """
        获取语义重叠部分，在句子或单词边界处截断
        
        Args:
            text: 输入文本
            overlap_size: 重叠大小
            prefix: True表示获取后缀（从末尾），False表示获取前缀（从开头）
            
        Returns:
            语义边界的重叠部分
        """
        import re
        
        if len(text) <= overlap_size:
            return text
        
        if prefix:
            # 获取文本末尾的部分
            sub_text = text[-overlap_size:]
            start_pos = len(text) - overlap_size
        else:
            # 获取文本开头的部分
            sub_text = text[:overlap_size]
            start_pos = 0
        
        # 尝试在句子边界处分割
        if prefix:
            # 在末尾部分寻找句子结束符
            sentence_end_match = re.search(r'[.!?。！？][^a-zA-Z0-9]*$', sub_text)
            if sentence_end_match:
                end_pos = sentence_end_match.end()
                return text[start_pos:start_pos + end_pos]
        
            # 寻找单词边界
            word_boundary_match = re.search(r'\s[^a-zA-Z0-9]*$', sub_text)
            if word_boundary_match:
                end_pos = word_boundary_match.start()
                return text[start_pos:start_pos + end_pos]
        else:
            # 在开头部分寻找句子开始符
            sentence_start_match = re.search(r'^[^.!?。！？]*[.!?。！？]\s*', sub_text)
            if sentence_start_match:
                end_pos = sentence_start_match.end()
                return text[start_pos:start_pos + end_pos]
        
            # 寻找单词边界
            word_boundary_match = re.search(r'\s', sub_text)
            if word_boundary_match:
                end_pos = word_boundary_match.end()
                return text[start_pos:start_pos + end_pos]
        
        # 如果没找到合适的边界，就返回原始截取的部分
        if prefix:
            return text[len(text) - overlap_size:]
        else:
            return text[:overlap_size]


class OverlapControllerFactory:
    """重叠控制器工厂类"""
    
    @staticmethod
    def get_controller(controller_type: str = "simple") -> OverlapController:
        """
        获取指定类型的重叠控制器
        
        Args:
            controller_type: 控制器类型 ("simple" 或 "semantic")
            
        Returns:
            对应的重叠控制器实例
        """
        if controller_type.lower() == "semantic":
            return SemanticOverlapController()
        else:
            return SimpleOverlapController()