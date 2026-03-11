"""
Markdown文档解析器
将Markdown文档解析为Element对象列表，考虑目录结构
"""

import re
from typing import Dict, Any, List
from pathlib import Path

from .processor import DocumentParser, ParseResult, Element
from .config import DocPreprocessorConfig


class MarkdownParser(DocumentParser):
    """Markdown文档解析器"""
    
    def __init__(self, config: DocPreprocessorConfig = None):
        self.config = config or DocPreprocessorConfig()
        # 编译正则表达式以提高性能
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)
        self.list_item_pattern = re.compile(r'^(\s*)([*+-]|\d+\.)\s+(.*)', re.MULTILINE)
        self.table_pattern = re.compile(r'^\|(.*?)\|\s*$', re.MULTILINE)
        self.blockquote_pattern = re.compile(r'^(>\s+.+)', re.MULTILINE)
    
    def parse(self, file_path: str, user_id: str, knowledge_base_id: str) -> Dict[str, Any]:
        """
        解析Markdown文档
        
        Args:
            file_path: 文件路径（来自用户上传）
            user_id: 用户ID
            knowledge_base_id: 知识库ID（团队ID）
            
        Returns:
            解析后的JSON格式数据，格式为：
            {
                "user_id": str,
                "file_name": str,
                "knowledge_base_id": str,
                "elements": List[Element]
            }
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        elements = self._parse_markdown(content)
        
        result = ParseResult(
            user_id=user_id,
            file_name=Path(file_path).name,
            knowledge_base_id=knowledge_base_id,
            elements=elements
        )
        
        return result.to_dict()
    
    def _parse_markdown(self, content: str) -> List[Element]:
        """
        解析Markdown内容为Element列表
        """
        elements = []
        element_index = 0
        
        # 按行分割内容
        lines = content.split('\n')
        
        # 跟踪标题层级路径
        heading_stack = []  # 存储 (heading_level, title) 元组
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            # 检查是否为标题
            heading_match = self.heading_pattern.match(lines[i])
            if heading_match:
                hashes, title = heading_match.groups()
                heading_level = len(hashes)
                
                # 更新标题栈
                # 移除所有层级大于等于当前标题的标题
                while heading_stack and heading_stack[-1][0] >= heading_level:
                    heading_stack.pop()
                
                # 添加当前标题
                heading_stack.append((heading_level, title))
                
                # 构建structure_path
                structure_path = [h[1] for h in heading_stack]
                
                element = self._create_heading_element(heading_match, element_index, structure_path)
                elements.append(element)
                element_index += 1
                i += 1
                continue
            
            # 检查是否为代码块
            if lines[i].startswith('```'):
                # 查找代码块结束
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    j += 1
                    if j >= len(lines):
                        break
                
                if j < len(lines):
                    # 构建完整代码块
                    code_lines = lines[i:j+1]
                    code_block = '\n'.join(code_lines)
                    
                    element = self._create_code_block_element(code_block, element_index)
                    elements.append(element)
                    element_index += 1
                    
                    i = j + 1
                    continue
            
            # 检查是否为引用块
            if lines[i].startswith('> '):
                # 收集连续的引用行
                quote_lines = []
                j = i
                while j < len(lines) and lines[j].startswith('> '):
                    quote_lines.append(lines[j][2:])  # 移除 '> ' 前缀
                    j += 1
                
                quote_content = '\n'.join(quote_lines)
                
                element = self._create_quote_element(quote_content, element_index)
                elements.append(element)
                element_index += 1
                
                i = j
                continue
            
            # 检查是否为列表项
            list_match = self.list_item_pattern.match(lines[i])
            if list_match:
                # 收集同级列表项
                list_items = []
                indent_level = len(list_match.group(1))  # 获取缩进级别
                j = i
                
                while j < len(lines):
                    current_line = lines[j]
                    # 检查是否是同级列表项
                    current_match = self.list_item_pattern.match(current_line)
                    if current_match:
                        current_indent = len(current_match.group(1))
                        if current_indent == indent_level:
                            list_items.append(current_line.strip())
                            j += 1
                        elif current_indent < indent_level:
                            # 更高级别的列表，跳出
                            break
                        else:
                            # 子列表项，暂时加入（简化处理）
                            list_items.append(current_line.strip())
                            j += 1
                    else:
                        # 不是列表项，检查是否为空行或只有缩进
                        if current_line.strip() == '':
                            j += 1
                        else:
                            break
                
                # 为每个列表项创建Element
                for item in list_items:
                    element = self._create_list_item_element(item, element_index)
                    elements.append(element)
                    element_index += 1
                
                i = j
                continue
            
            # 检查是否为表格（简单判断：包含 | 分隔符）
            if '|' in lines[i] and self.table_pattern.match(lines[i]):
                # 收集表格行直到遇到非表格行
                table_lines = []
                j = i
                while j < len(lines) and '|' in lines[j] and self.table_pattern.match(lines[j]):
                    table_lines.append(lines[j])
                    j += 1
                
                table_content = '\n'.join(table_lines)
                
                element = self._create_table_element(table_content, element_index)
                elements.append(element)
                element_index += 1
                
                i = j
                continue
            
            # 默认作为段落处理
            element = self._create_paragraph_element(lines[i], element_index)
            elements.append(element)
            element_index += 1
            i += 1
        
        return elements
    
    def _create_heading_element(self, match, element_index: int, structure_path: List[str] = None) -> Element:
        """创建标题Element"""
        hashes, title = match.groups()
        heading_level = len(hashes)
        
        metadata = {
            "heading_level": heading_level,
            "syntax_raw": hashes,
            "heading_id": self._generate_heading_id(title),
            "detected_language": "zh-CN",
            "character_count": len(title),
            "is_structural": True
        }
        
        # 如果提供了structure_path，添加到metadata中
        if structure_path:
            metadata["structure_path"] = structure_path
        
        element = Element(
            raw_content=match.group(0),  # 完整的标题行
            element_type="heading",
            element_index=element_index,
            source_format="markdown",
            format_metadata=metadata,
            parser_confidence=1.0
        )
        
        return element
    
    def _create_code_block_element(self, code_block: str, element_index: int) -> Element:
        """创建代码块Element"""
        # 提取语言信息
        lines = code_block.split('\n')
        lang_line = lines[0]
        language = ""
        if lang_line.startswith('```'):
            language = lang_line[3:].strip() or "plain"
        
        metadata = {
            "language": language,
            "fence_char": "```",
            "info_string": language,
            "detected_language": "en-US",
            "character_count": len(code_block),
            "is_structural": True
        }
        
        element = Element(
            raw_content=code_block,
            element_type="code_block",
            element_index=element_index,
            source_format="markdown",
            format_metadata=metadata,
            parser_confidence=1.0
        )
        
        return element
    
    def _create_paragraph_element(self, content: str, element_index: int) -> Element:
        """创建段落Element"""
        metadata = {
            "detected_language": "zh-CN",
            "character_count": len(content),
            "is_structural": False
        }
        
        element = Element(
            raw_content=content,
            element_type="paragraph",
            element_index=element_index,
            source_format="markdown",
            format_metadata=metadata,
            parser_confidence=0.95
        )
        
        return element
    
    def _create_list_item_element(self, content: str, element_index: int) -> Element:
        """创建列表项Element"""
        metadata = {
            "detected_language": "zh-CN",
            "character_count": len(content),
            "is_structural": True
        }
        
        element = Element(
            raw_content=content,
            element_type="list_item",
            element_index=element_index,
            source_format="markdown",
            format_metadata=metadata,
            parser_confidence=0.98
        )
        
        return element
    
    def _create_quote_element(self, content: str, element_index: int) -> Element:
        """创建引用块Element"""
        metadata = {
            "detected_language": "zh-CN",
            "character_count": len(content),
            "is_structural": True
        }
        
        element = Element(
            raw_content=f"> {content}",
            element_type="blockquote",
            element_index=element_index,
            source_format="markdown",
            format_metadata=metadata,
            parser_confidence=1.0
        )
        
        return element
    
    def _create_table_element(self, content: str, element_index: int) -> Element:
        """创建表格Element"""
        lines = content.split('\n')
        # 计算列数（基于第一行）
        first_row = lines[0] if lines else ""
        columns = first_row.count('|') - 1 if '|' in first_row else 0
        
        metadata = {
            "column_count": columns,
            "row_count": len(lines),
            "detected_language": "zh-CN",
            "character_count": len(content),
            "is_structural": True
        }
        
        element = Element(
            raw_content=content,
            element_type="table",
            element_index=element_index,
            source_format="markdown",
            format_metadata=metadata,
            parser_confidence=0.90
        )
        
        return element
    
    def _generate_heading_id(self, title: str) -> str:
        """生成标题ID"""
        # 简单的slug生成，移除非字母数字字符并替换空格为连字符
        import re
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return slug if slug else title.lower().replace(' ', '-')
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        return ['.md', '.markdown']