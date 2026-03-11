"""
纯文本解析器
将纯文本文件解析为Element对象列表
"""

import os
import re
from typing import Dict, Any, List
from .processor import DocumentParser, ParseResult, Element 
from .config import DocPreprocessorConfig


class PlainTextParser(DocumentParser):
    """纯文本解析器 - 解析.txt等纯文本文件"""
    
    def __init__(self, config: DocPreprocessorConfig = None):
        self.config = config or DocPreprocessorConfig()
        # 编译正则表达式以提高性能
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')
        self.numbered_heading_pattern = re.compile(r'^(\d+\.\d*)\s+(.+)$')
        self.list_item_pattern = re.compile(r'^(\s*)([*+-]|\d+\.)\s+(.*)')
    
    def parse(self, file_path: str, user_id: str, knowledge_base_id: str) -> Dict[str, Any]:
        """
        解析文本文件
        
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
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 创建Element对象列表
        elements = self._create_elements(content, file_path)
        
        # 创建解析结果
        result = ParseResult(
            user_id=user_id,
            file_name=os.path.basename(file_path),
            knowledge_base_id=knowledge_base_id,
            elements=elements
        )
        
        return result.to_dict()
    
    def _create_elements(self, content: str, file_path: str) -> List[Element]:
        """创建Element对象 - 按段落分割文本，识别标题和列表"""
        # 按行分割内容
        lines = content.split('\n')
        elements = []
        
        source_format = self._extract_source_format(file_path)
        
        element_index = 0
        
        # 跟踪标题层级路径
        heading_stack = []  # 存储 (heading_level, title) 元组
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            if not line.strip():  # 跳过空行
                i += 1
                continue
            
            # 检查是否为Markdown风格标题（# 开头）
            heading_match = self.heading_pattern.match(line)
            if heading_match:
                hashes, title = heading_match.groups()
                heading_level = len(hashes)
                
                # 更新标题栈
                while heading_stack and heading_stack[-1][0] >= heading_level:
                    heading_stack.pop()
                
                # 添加当前标题
                heading_stack.append((heading_level, title))
                
                # 构建structure_path
                structure_path = [h[1] for h in heading_stack]
                
                # 创建标题Element
                element = Element(
                    raw_content=line,
                    element_type="heading",
                    element_index=element_index,
                    source_format=source_format,
                    format_metadata={
                        "heading_level": heading_level,
                        "detected_language": "zh-CN",
                        "character_count": len(title),
                        "structure_path": structure_path,
                        "is_structural": True
                    },
                    parser_confidence=1.0
                )
                elements.append(element)
                element_index += 1
                i += 1
                continue
            
            # 检查是否为数字编号标题（如 "1. 引言" 或 "3.1 机器学习"）
            # 注意：需要排除列表项（如"1. 准备模型文件"），这些通常是段落内容的一部分
            numbered_heading_match = self.numbered_heading_pattern.match(line)
            if numbered_heading_match and not line.strip().startswith('-') and not line.strip().startswith('*'):
                number, title = numbered_heading_match.groups()
                
                # 判断是否为真正的标题（而不是列表项）
                # 标题通常满足以下条件之一：
                # 1. 标题长度较长（超过10个字符）
                # 2. 标题包含中文字符（中文标题通常较长）
                # 3. 下一行是空行或另一个标题（表示这是独立的标题）
                is_title = self._is_numbered_heading(lines, i, title)
                
                if is_title:
                    # 根据编号层级确定标题级别
                    # 例如 "1." 是1级，"3.1" 是2级
                    parts = number.split('.')
                    heading_level = min(len([p for p in parts if p.strip()]), 6)
                    
                    # 更新标题栈
                    while heading_stack and heading_stack[-1][0] >= heading_level:
                        heading_stack.pop()
                    
                    # 添加当前标题
                    heading_stack.append((heading_level, title))
                    
                    # 构建structure_path
                    structure_path = [h[1] for h in heading_stack]
                    
                    # 创建标题Element
                    element = Element(
                        raw_content=line,
                        element_type="heading",
                        element_index=element_index,
                        source_format=source_format,
                        format_metadata={
                            "heading_level": heading_level,
                            "detected_language": "zh-CN",
                            "character_count": len(title),
                            "structure_path": structure_path,
                            "is_structural": True
                        },
                        parser_confidence=0.95
                    )
                    elements.append(element)
                    element_index += 1
                    i += 1
                    continue
            
            # 检查是否为列表项
            list_match = self.list_item_pattern.match(line.strip())
            if list_match:
                indent, marker, content = list_match.groups()
                
                # 创建列表项Element
                element = Element(
                    raw_content=line.strip(),
                    element_type="list_item",
                    element_index=element_index,
                    source_format=source_format,
                    format_metadata={
                        "detected_language": "zh-CN",
                        "character_count": len(line.strip()),
                        "list_marker": marker,
                        "indent_level": len(indent) // 2,
                        "structure_path": [h[1] for h in heading_stack],
                        "is_structural": False
                    },
                    parser_confidence=0.95
                )
                elements.append(element)
                element_index += 1
                i += 1
                continue
            
            # 默认作为段落处理
            element = Element(
                raw_content=line.strip(),
                element_type="paragraph",
                element_index=element_index,
                source_format=source_format,
                format_metadata={
                    "detected_language": "zh-CN",
                    "character_count": len(line.strip()),
                    "structure_path": [h[1] for h in heading_stack],
                    "is_structural": False
                },
                parser_confidence=0.95
            )
            elements.append(element)
            element_index += 1
            i += 1
        
        return elements
    
    def _is_numbered_heading(self, lines: List[str], index: int, title: str) -> bool:
        """判断编号行是否为真正的标题（而不是列表项）"""
        if not title:
            return False
        
        # 优先检查连续编号的情况（列表项）
        if index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            
            # 检查下一行是否也是编号行
            next_match = self.numbered_heading_pattern.match(next_line)
            if next_match:
                # 如果下一行也是编号行，这通常是列表，而不是标题
                return False
        
        # 检查当前行是否是列表项格式（编号+中文内容）
        # 列表项通常较短（少于20个字符）且包含中文
        import re
        if re.search(r'[\u4e00-\u9fa5]', title) and len(title) < 20:
            # 这很可能是列表项，而不是标题
            return False
        
        # 条件1：标题长度较长（超过20个字符）
        if len(title) > 20:
            return True
        
        # 条件2：标题包含中文字符（中文标题通常较长）
        if re.search(r'[\u4e00-\u9fa5]', title):
            # 中文标题通常至少有5个字符
            if len(title) >= 5:
                return True
        
        # 条件3：标题包含"章节"、"部分"、"章"、"节"等关键词
        if any(keyword in title for keyword in ['章节', '部分', '章', '节', '引言', '概述', '总结']):
            return True
        
        return False
    
    def _extract_source_format(self, file_path: str) -> str:
        """提取源文件格式"""
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            '.txt': 'plain_text',
            '.text': 'plain_text',
        }
        return type_map.get(ext, 'plain_text')
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        return ['.txt', '.text']