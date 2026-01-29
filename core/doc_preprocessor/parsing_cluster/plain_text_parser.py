"""
纯文本解析器
将纯文本文件解析为Element对象列表
"""

import os
from typing import Dict, Any, List
from .processor import DocumentParser, ParseResult, Element 
from .config import DocPreprocessorConfig


class PlainTextParser(DocumentParser):
    """纯文本解析器 - 解析.txt等纯文本文件"""
    
    def __init__(self, config: DocPreprocessorConfig = None):
        self.config = config or DocPreprocessorConfig()
    
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
        """创建Element对象 - 按段落分割文本"""
        # 按双换行符分割段落
        paragraphs = content.split('\n\n')
        elements = []
        
        source_format = self._extract_source_format(file_path)
        
        element_index = 0
        for para in paragraphs:
            if para.strip():  # 忽略空段落
                # 进一步将段落分割为句子或行
                lines = [line.strip() for line in para.split('\n') if line.strip()]
                
                for i, line in enumerate(lines):
                    if line.strip():
                        # 创建Element对象
                        element = Element(
                            raw_content=line.strip(),
                            element_type="paragraph",  # 纯文本默认为段落类型
                            element_index=element_index,
                            source_format=source_format,
                            format_metadata={
                                "detected_language": "zh-CN",
                                "character_count": len(line.strip()),
                                "line_number": element_index + 1,
                                "is_structural": False
                            },
                            parser_confidence=0.95
                        )
                        elements.append(element)
                        element_index += 1
        
        return elements
    
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