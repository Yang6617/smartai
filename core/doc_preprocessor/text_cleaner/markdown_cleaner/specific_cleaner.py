"""
Markdown专用清洗器实现

根据element_type进行差异化处理：
1. heading元素（标题）：规范化标题标记，移除多余#号
2. code_block元素（代码块）：保留内部格式，清理围栏外部空格
3. 其他元素：修复链接空格，规范列表标记
"""

import re
from typing import List, Dict, Any
from core.doc_preprocessor.parsing_cluster.processor import Element
from .interfaces import MarkdownTextCleaner
from .config import MarkdownCleanerConfig


class MarkdownSpecificCleaner(MarkdownTextCleaner):
    """
    Markdown专用清洗器
    根据element_type进行差异化处理
    """
    
    def __init__(self, config: MarkdownCleanerConfig = None):
        self.config = config or MarkdownCleanerConfig()
        
        # 预编译正则表达式以提高性能
        self._heading_pattern = re.compile(r'^(#{1,6})\s*(.*?)\s*(#+)\s*$')
        self._space_after_heading_pattern = re.compile(r'^(#{1,6})([^\s#])')
        self._link_pattern = re.compile(r'\[\s*([^\]]+?)\s*\]\s*\(\s*([^\)]+?)\s*\)')
        self._list_item_pattern = re.compile(r'^(\s*)([*+-])\s+')

    def clean(self, elements: List[Element]) -> List[Element]:
        """
        根据element_type对Markdown内容进行差异化清洗
        
        Args:
            elements: 待清洗的Element对象列表
            
        Returns:
            清洗后的Element对象列表
        """
        cleaned_elements = []
        
        for element in elements:
            cleaned_element = self._clean_single_element(element)
            cleaned_elements.append(cleaned_element)
        
        return cleaned_elements

    def _clean_single_element(self, element: Element) -> Element:
        """
        清洗单个Element对象
        
        Args:
            element: 待清洗的Element对象
            
        Returns:
            清洗后的Element对象
        """
        # 根据element_type进行差异化处理
        if element.element_type == "heading":
            cleaned_content = self._clean_heading(element.raw_content)
        elif element.element_type == "code_block":
            cleaned_content = self._clean_code_block(element.raw_content)
        else:
            cleaned_content = self._clean_other_elements(element.raw_content)
        
        # 创建新的Element对象，避免修改原对象
        cleaned_element = Element(
            raw_content=cleaned_content,
            element_type=element.element_type,
            element_index=element.element_index,
            source_format=element.source_format,
            format_metadata=element.format_metadata,
            parser_confidence=element.parser_confidence
        )
        
        return cleaned_element

    def _clean_heading(self, content: str) -> str:
        """
        清洗标题元素
        
        Args:
            content: 标题内容
            
        Returns:
            清洗后的标题内容
        """
        if not self.config.normalize_heading_format:
            return content
            
        # 规范化标题格式：确保 # 后有一个空格
        if self.config.ensure_space_after_heading_marker:
            # 处理没有空格的情况，如 "##Title" -> "## Title"
            content = self._space_after_heading_pattern.sub(r'\1 \2', content)
        
        # 移除标题末尾多余的 # 号，如 "# 标题 #" -> "# 标题"
        if self.config.remove_extra_heading_hashes:
            match = self._heading_pattern.match(content)
            if match:
                level_part = match.group(1)  # 如 "###"
                title_part = match.group(2)  # 如 "标题"
                extra_hashes = match.group(3)  # 如 "##" (多余的#)
                
                # 只保留与级别匹配的#号
                cleaned_content = f"{level_part} {title_part}".strip()
                content = cleaned_content
        
        return content

    def _clean_code_block(self, content: str) -> str:
        """
        清洗代码块元素
        
        Args:
            content: 代码块内容
            
        Returns:
            清洗后的代码块内容
        """
        if not self.config.preserve_code_block_formatting:
            return content
            
        # 保留内部格式（缩进、空格），只清理围栏外部的多余空格
        lines = content.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            # 对于代码块内部（非首尾围栏行），保留所有格式
            if i == 0 or i == len(lines) - 1:
                # 如果是首行或末行（通常是代码围栏），只去除行首行尾空格
                if self.config.normalize_code_fence_spacing:
                    cleaned_lines.append(line.strip())
                else:
                    cleaned_lines.append(line)
            else:
                # 保留中间代码行的所有格式
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def _clean_other_elements(self, content: str) -> str:
        """
        清洗其他类型元素（段落、列表项等）
        
        Args:
            content: 元素内容
            
        Returns:
            清洗后的元素内容
        """
        # 修复Markdown链接中的多余空格
        if self.config.fix_link_spacing:
            content = self._fix_link_spacing(content)
        
        # 规范列表项标记一致性
        if self.config.normalize_list_markers:
            content = self._normalize_list_items(content)
        
        return content

    def _fix_link_spacing(self, content: str) -> str:
        """
        修复Markdown链接中的多余空格
        
        Args:
            content: 链接内容
            
        Returns:
            修复后的链接内容
        """
        # 使用正则表达式修复链接格式，确保文本和URL之间没有多余空格
        def replace_link(match):
            link_text = match.group(1).strip()  # 去除链接文本的前后空格
            link_url = match.group(2).strip()   # 去除链接URL的前后空格
            return f"[{link_text}]({link_url})"
        
        return self._link_pattern.sub(replace_link, content)

    def _normalize_list_items(self, content: str) -> str:
        """
        规范列表项标记一致性
        
        Args:
            content: 列表内容
            
        Returns:
            规范化后的列表内容
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 查找列表项标记并规范化
            match = self._list_item_pattern.match(line)
            if match:
                indent = match.group(1)  # 缩进部分
                marker = match.group(2)  # 列表标记 (*, -, +)
                
                # 标准化为 "- " 格式
                cleaned_line = self._list_item_pattern.sub(f"{indent}- ", line, count=1)
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def get_cleaner_info(self) -> Dict[str, Any]:
        """
        获取清洗器的基本信息
        
        Returns:
            包含清洗器名称、描述等信息的字典
        """
        return {
            "name": "MarkdownSpecificCleaner",
            "description": "Markdown专用文本清洗器，针对不同元素类型进行差异化处理",
            "features": [
                "标题格式规范化",
                "代码块格式保留",
                "链接格式修复",
                "列表标记规范化"
            ],
            "config": {
                "normalize_heading_format": self.config.normalize_heading_format,
                "preserve_code_block_formatting": self.config.preserve_code_block_formatting,
                "fix_link_spacing": self.config.fix_link_spacing,
                "normalize_list_markers": self.config.normalize_list_markers
            }
        }