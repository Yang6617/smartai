"""
通用基础清洗器
实现对所有Element的基础文本清洗功能
"""

import re
from typing import List, Dict, Any
import unicodedata

from .interfaces import TextCleaner
from .config import TextCleanerConfig as CleanerConfig
from ..parsing_cluster.processor import Element


class BasicTextCleaner(TextCleaner):
    """
    通用基础清洗器
    实现基础的文本清洗功能，包括：
    1. 空白字符标准化
    2. 基础编码规范化
    3. 换行符统一
    """
    
    def __init__(self, config: CleanerConfig = None):
        self.config = config or CleanerConfig()
        
        # 预编译正则表达式以提高性能
        self._whitespace_pattern = re.compile(r'\s+')  # 匹配任意空白字符
        self._newline_pattern = re.compile(r'\r\n|\r|\n')  # 匹配不同类型的换行符
        self._consecutive_newlines_pattern = re.compile(
            r'\n{' + str(self.config.max_consecutive_newlines + 1) + ',}'
        )  # 匹配超过最大数量的连续换行符
        
        # 全角字符到半角字符的映射表
        # 全角数字 '０'-'９' (U+FF10-U+FF19) -> 半角数字 '0'-'9' (U+0030-U+0039)
        # 全角大写字母 'Ａ'-'Ｚ' (U+FF21-U+FF3A) -> 半角大写字母 'A'-'Z' (U+0041-U+005A) 
        # 全角小写字母 'ａ'-'ｚ' (U+FF41-U+FF5A) -> 半角小写字母 'a'-'z' (U+0061-U+007A)
        self._fullwidth_to_halfwidth_map = {}
        
        # 数字
        for i in range(0xFF10, 0xFF1A):  # '０' to '９'
            self._fullwidth_to_halfwidth_map[i] = i - 0xFF10 + ord('0')  # '0'(0x30)
        
        # 大写字母
        for i in range(0xFF21, 0xFF3B):  # 'Ａ' to 'Ｚ'
            self._fullwidth_to_halfwidth_map[i] = i - 0xFF21 + ord('A')  # 'A'(0x41)
        
        # 小写字母
        for i in range(0xFF41, 0xFF5B):  # 'ａ' to 'ｚ'
            self._fullwidth_to_halfwidth_map[i] = i - 0xFF41 + ord('a')  # 'a'(0x61)
        
        # 常见乱码修复映射
        self._mojibake_fixes = {
            'Â': 'A',  # 常见的乱码字符
            'â': 'a',
            'Ê': 'E',
            'ê': 'e',
            'Î': 'I',
            'î': 'i',
            'Ô': 'O',
            'ô': 'o',
            'Û': 'U',
            'û': 'u',
            'Ç': 'C',
            'ç': 'c',
            'Ñ': 'N',
            'ñ': 'n',
            'Ü': 'U',
            'ü': 'u',
            'Ö': 'O',
            'ö': 'o',
            'Ä': 'A',
            'ä': 'a',
        }
    
    def clean(self, elements: List[Element]) -> List[Element]:
        """
        清洗Element列表中的文本内容
        
        Args:
            elements: 待清洗的Element对象列表
            
        Returns:
            清洗后的Element对象列表
        """
        cleaned_elements = []
        
        for element in elements:
            # 创建Element的副本以避免修改原始对象
            cleaned_element = Element(
                raw_content=self._clean_single_content(element.raw_content),
                element_type=element.element_type,
                element_index=element.element_index,
                source_format=element.source_format,
                format_metadata=element.format_metadata.copy() if element.format_metadata else {},
                parser_confidence=element.parser_confidence
            )
            cleaned_elements.append(cleaned_element)
        
        return cleaned_elements
    
    def _clean_single_content(self, content: str) -> str:
        """
        清洗单个文本内容
        
        Args:
            content: 待清洗的文本内容
            
        Returns:
            清洗后的文本内容
        """
        if not content:
            return content
        
        # 按顺序执行各项清洗操作
        if self.config.normalize_whitespace:
            content = self._normalize_whitespace(content)
        
        if self.config.normalize_full_width_chars:
            content = self._normalize_encoding(content)
        
        if self.config.normalize_line_breaks:
            content = self._normalize_line_breaks(content)
        
        return content
    
    def _normalize_whitespace(self, content: str) -> str:
        """
        标准化空白字符
        
        1. 去除首尾空格、制表符、换行符
        2. 将连续多个空格/制表符转为单个空格
        3. 将全角空格(U+3000)转为半角空格(U+0020)
        """
        if not content:
            return content
        
        # 1. 将全角空格转为半角空格
        if self.config.convert_full_width_spaces:
            content = content.replace('\u3000', ' ')  # 全角空格转半角空格
        
        # 2. 去除首尾空白字符
        if self.config.remove_leading_trailing:
            content = content.strip()
        
        # 3. 将连续多个空白字符（空格、制表符等）转为单个空格
        content = self._whitespace_pattern.sub(' ', content)
        
        return content
    
    def _normalize_encoding(self, content: str) -> str:
        """
        基础编码规范化
        
        1. 将全角英文字母/数字转为半角
        2. 修复常见乱码字符（如"Â" -> "A"）
        3. 统一中文标点为全角，英文标点为半角
        """
        if not content:
            return content
        
        # 1. 将全角字符转为半角
        content = content.translate(self._fullwidth_to_halfwidth_map)
        
        # 2. 修复常见乱码字符
        if self.config.fix_common_mojibake:
            for mojibake_char, correct_char in self._mojibake_fixes.items():
                content = content.replace(mojibake_char, correct_char)
        
        # 3. 统一标点符号（如果需要）
        if self.config.unify_punctuation:
            content = self._unify_punctuation(content)
        
        return content
    
    def _unify_punctuation(self, content: str) -> str:
        """
        统一标点符号
        中文标点为全角，英文标点为半角
        """
        # 定义中文全角标点符号到英文半角标点符号的映射
        chinese_to_english_punctuation = {
            '，': ',',  # 逗号
            '。': '.',  # 句号
            '！': '!',  # 感叹号
            '？': '?',  # 问号
            '；': ';',  # 分号
            '：': ':',  # 冒号
            '‘': "'",  # 单引号左
            '’': "'",  # 单引号右
            '“': '"',  # 双引号左
            '”': '"',  # 双引号右
            '（': '(',  # 左括号
            '）': ')',  # 右括号
            '【': '[',  # 左方括号
            '】': ']',  # 右方括号
            '《': '<',  # 左尖括号
            '》': '>',  # 右尖括号
            '、': '/',  # 顿号
            '…': '...',  # 省略号
            '—': '-',   # 破折号
            '－': '-',  # 连接号
        }

        # 定义英文半角标点符号到中文全角标点符号的映射
        english_to_chinese_punctuation = {
            ',': '，',
            '.': '。',
            '!': '！',
            '?': '？',
            ';': '；',
            ':': '：',
            "'": '’',  # 单引号
            '"': '"',  # 双引号
            '(': '（',
            ')': '）',
            '[': '【',
            ']': '】',
            '<': '《',
            '>': '》',
            '/': '、',  # 斜杠当作顿号
        }

        # 为了区分中英文语境，我们只将英文标点转换为中文标点（因为内容主要是中文）
        # 这里实现中文标点符号的标准化
        for chinese_punct, english_punct in chinese_to_english_punctuation.items():
            content = content.replace(chinese_punct, english_punct)
        
        # 如果需要将英文标点转换为中文标点，可以使用下面的逻辑
        # 但这里我们保持英文标点为半角，中文标点为全角
        # 根据上下文判断可能比较复杂，所以暂时使用简单的规则
        
        return content
    
    def _normalize_line_breaks(self, content: str) -> str:
        """
        统一换行符
        
        1. 将所有换行符（\r\n, \r）统一为 \n
        2. 移除连续多个换行符（最多保留2个）
        """
        if not content:
            return content
        
        # 1. 统一换行符为 \n
        content = self._newline_pattern.sub('\n', content)
        
        # 2. 将超过最大数量的连续换行符替换为指定数量的换行符
        if self.config.max_consecutive_newlines > 0:
            replacement = '\n' * self.config.max_consecutive_newlines
            content = self._consecutive_newlines_pattern.sub(replacement, content)
        
        return content
    
    def get_cleaner_info(self) -> Dict[str, Any]:
        """
        获取清洗器的基本信息
        
        Returns:
            包含清洗器名称、描述等信息的字典
        """
        return {
            "name": "BasicTextCleaner",
            "description": "通用基础文本清洗器",
            "features": [
                "空白字符标准化",
                "基础编码规范化", 
                "换行符统一"
            ],
            "config": {
                "normalize_whitespace": self.config.normalize_whitespace,
                "normalize_full_width_chars": self.config.normalize_full_width_chars,
                "normalize_line_breaks": self.config.normalize_line_breaks,
                "max_consecutive_newlines": self.config.max_consecutive_newlines
            }
        }