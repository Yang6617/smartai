"""
OCR专用清洗器实现

专门处理source_format为"image"的Element，解决OCR识别结果中的常见问题：
1. OCR空格粘连修复（核心）- 修复因字符分割导致的错误空格
2. 常见OCR字符错误纠正（基于简单映射表）
"""

import re
from typing import List, Dict, Any
from core.doc_preprocessor.parsing_cluster.processor import Element
from .interfaces import OCRTextCleaner
from .config import OCRCleanerConfig


class OCRSpecificCleaner(OCRTextCleaner):
    """
    OCR专用清洗器
    专门处理OCR识别结果中的格式问题
    """
    
    def __init__(self, config: OCRCleanerConfig = None):
        self.config = config or OCRCleanerConfig()
        
        # OCR字符错误纠正映射表
        self._ocr_error_mapping = {
            "0": "o",    # 仅在字母上下文
            "1": "l",    # 小写L
            "5": "s",    # 在某些上下文中
            "8": "s",    # 在某些上下文中
            "6": "b",    # 在某些上下文中
        }
        
        # 预编译正则表达式以提高性能
        self._chinese_space_pattern = re.compile(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])')
        self._digit_space_pattern = re.compile(r'(?<=\d)\s+(?=\d)')
        self._letter_space_pattern = re.compile(r'(?<=[a-zA-Z])\s+(?=[a-zA-Z])')
        
        # 用于检测是否为连续字母的模式
        self._consecutive_letter_pattern = re.compile(r'[a-zA-Z](?:\s+[a-zA-Z])+')
        
        # 用于检测是否为连续中文字符的模式
        self._consecutive_chinese_pattern = re.compile(r'[\u4e00-\u9fff](?:\s+[\u4e00-\u9fff])+')
        
        # 用于检测中文和数字之间的空格（OCR常见错误）
        self._chinese_digit_space_pattern = re.compile(r'(?<=[\u4e00-\u9fff])\s+(?=\d)')
        self._digit_chinese_space_pattern = re.compile(r'(?<=\d)\s+(?=[\u4e00-\u9fff])')
        
        # 用于检测中文和字母之间的空格（OCR常见错误）
        self._chinese_letter_space_pattern = re.compile(r'(?<=[\u4e00-\u9fff])\s+(?=[a-zA-Z])')
        self._letter_chinese_space_pattern = re.compile(r'(?<=[a-zA-Z])\s+(?=[\u4e00-\u9fff])')
        
        # 用于检测数字和字母之间的空格（OCR常见错误）
        self._digit_letter_space_pattern = re.compile(r'(?<=\d)\s+(?=[a-zA-Z])')
        self._letter_digit_space_pattern = re.compile(r'(?<=[a-zA-Z])\s+(?=\d)')

    def clean(self, elements: List[Element]) -> List[Element]:
        """
        清洗Element列表中的OCR文本内容，仅处理source_format为"image"的元素
        
        Args:
            elements: 待清洗的Element对象列表
            
        Returns:
            清洗后的Element对象列表
        """
        cleaned_elements = []
        
        for element in elements:
            # 仅处理source_format为"image"的元素
            if element.source_format.lower() == "image":
                cleaned_element = self._clean_single_element(element)
                cleaned_elements.append(cleaned_element)
            else:
                # 非image格式的元素直接返回
                cleaned_elements.append(element)
        
        return cleaned_elements

    def _clean_single_element(self, element: Element) -> Element:
        """
        清洗单个Element对象
        
        Args:
            element: 待清洗的Element对象
            
        Returns:
            清洗后的Element对象
        """
        content = element.raw_content
        
        # 执行OCR特定的清洗操作
        if self.config.fix_space_glue_errors:
            content = self._fix_space_glue_errors(content)
        
        if self.config.correct_ocr_errors:
            content = self._correct_ocr_errors(content)
        
        # 创建新的Element对象，避免修改原对象
        cleaned_element = Element(
            raw_content=content,
            element_type=element.element_type,
            element_index=element.element_index,
            source_format=element.source_format,
            format_metadata=element.format_metadata,
            parser_confidence=element.parser_confidence
        )
        
        return cleaned_element

    def _fix_space_glue_errors(self, content: str) -> str:
        """
        修复OCR空格粘连错误
        - 修复中文字符之间的错误空格
        - 修复数字之间的错误空格
        - 修复字母之间的错误空格
        - 修复不同类型字符之间的错误空格（中文-数字、数字-字母等）
        
        Args:
            content: 待修复的内容
            
        Returns:
            修复后的内容
        """
        if not self.config.fix_space_glue_errors:
            return content
        
        # 合并中文字符间的空格
        if self.config.merge_chinese_characters:
            # 查找连续的中文字符，它们之间可能有空格
            content = self._chinese_space_pattern.sub('', content)
        
        # 合并相邻数字间的空格
        if self.config.merge_adjacent_digits:
            content = self._digit_space_pattern.sub('', content)
        
        # 合并相邻字母间的空格
        if self.config.merge_adjacent_letters:
            # 首先查找连续字母模式并合并它们之间的空格
            def merge_consecutive_letters(match):
                matched_text = match.group(0)
                # 移除字母间的空格
                merged = re.sub(r'\s+', '', matched_text)
                return merged
            
            content = self._consecutive_letter_pattern.sub(merge_consecutive_letters, content)
        
        # 合并中文和数字之间的空格（OCR常见错误）
        content = self._chinese_digit_space_pattern.sub('', content)
        content = self._digit_chinese_space_pattern.sub('', content)
        
        # 合并中文和字母之间的空格（OCR常见错误）
        content = self._chinese_letter_space_pattern.sub('', content)
        content = self._letter_chinese_space_pattern.sub('', content)
        
        # 合并数字和字母之间的空格（OCR常见错误）
        content = self._digit_letter_space_pattern.sub('', content)
        content = self._letter_digit_space_pattern.sub('', content)
        
        return content

    def _correct_ocr_errors(self, content: str) -> str:
        """
        纠正常见的OCR字符错误
        使用上下文感知的方式应用错误纠正
        
        Args:
            content: 待纠正的内容
            
        Returns:
            纠正后的内容
        """
        if not self.config.correct_ocr_errors:
            return content
        
        # 改进算法：先识别数字序列，然后进行上下文判断
        corrected_content = ""
        
        i = 0
        while i < len(content):
            char = content[i]
            
            # 检查是否需要进行OCR错误纠正
            if char in self._ocr_error_mapping:
                # 检查是否在数字序列中
                in_number_sequence = self._is_in_number_sequence(content, i)
                
                if in_number_sequence:
                    # 在数字序列中，不进行纠正
                    corrected_content += char
                else:
                    # 不在数字序列中，进行上下文判断
                    prev_char = content[i-1] if i > 0 else ''
                    next_char = content[i+1] if i < len(content) - 1 else ''
                    
                    corrected_char = self._apply_contextual_correction(char, prev_char, next_char)
                    corrected_content += corrected_char
            else:
                corrected_content += char
            
            i += 1
        
        return corrected_content

    def _is_in_number_sequence(self, content: str, pos: int) -> bool:
        """
        检查给定位置的字符是否在数字序列中
        
        Args:
            content: 内容字符串
            pos: 字符位置
            
        Returns:
            如果在数字序列中返回True，否则返回False
        """
        char = content[pos]
        if not char.isdigit():
            return False
        
        # 检查整个可能的数字字符串，看是否是连续的数字
        # 向左扩展找到数字串的开始
        start = pos
        while start > 0 and content[start-1].isdigit():
            start -= 1
        
        # 向右扩展找到数字串的结束
        end = pos
        while end < len(content) - 1 and content[end+1].isdigit():
            end += 1
        
        # 如果数字串长度大于1，且旁边有明显的数值标识（如单位），则认为是数字序列
        number_length = end - start + 1
        
        # 检查数字串前后是否有字母（可能表示这是一个单词而不是数字）
        before_start = content[start-1] if start > 0 else None
        after_end = content[end+1] if end < len(content) - 1 else None
        
        # 简单规则：
        # 1. 如果数字序列长度 > 1 且旁边有单位类字母（如 'ms', 'kg', 'px'），则视为数字序列
        # 2. 如果数字序列长度为1，但两侧都是字母，则可能不是数字序列（OCR错误）
        # 3. 如果数字序列长度 > 2，通常视为数字序列
        
        has_unit_like_after = after_end and after_end.isalpha()  # 如 "100ms", "20px"
        has_word_like_before = before_start and before_start.isalpha()  # 如 "page1", "fig2"
        
        # 长数字串通常保持为数字
        if number_length >= 3:
            return True
        
        # 检查数字序列是否被字母包围，如果是则可能是OCR错误
        has_alpha_before = before_start and before_start.isalpha()
        has_alpha_after = after_end and after_end.isalpha()
        
        if has_alpha_before and has_alpha_after:
            # 如果数字序列被字母包围，可能是OCR错误
            return False
            
        # 如果有单位标识符，则视为数字序列
        if has_unit_like_after or has_word_like_before:
            return True
            
        # 如果是多数字序列（长度>1）且不在字母之间，则视为数字序列
        if number_length > 1:
            return True
            
        return False

    def _apply_contextual_correction(self, char: str, prev_char: str, next_char: str) -> str:
        """
        根据上下文应用OCR错误纠正
        
        Args:
            char: 当前字符
            prev_char: 前一个字符
            next_char: 后一个字符
            
        Returns:
            纠正后的字符
        """
        if char not in self._ocr_error_mapping:
            return char
        
        # 获取映射的目标字符
        mapped_char = self._ocr_error_mapping[char]
        
        # 检查是否存在数字上下文（即前后都是数字或空格加数字）
        # 为了准确判断，我们需要查看更大的上下文
        # 但在当前字符级别的处理中，我们只能基于相邻字符判断
        
        # 对于"0" -> "o"的映射
        if char == "0" and mapped_char == "o":
            # 只在明确的字母上下文中纠正（前后至少有一个字母，且不是纯数字序列）
            # 如果前后都是数字，则不纠正
            if prev_char.isdigit() and next_char.isdigit():
                return char  # 在纯数字序列中不纠正
            elif (prev_char.isalpha() or next_char.isalpha()) and \
                 (prev_char.islower() or next_char.islower()):
                return mapped_char
        elif char == "1" and mapped_char == "l":
            # 只在字母上下文中纠正
            if prev_char.isdigit() and next_char.isdigit():
                return char  # 在纯数字序列中不纠正
            elif (prev_char.isalpha() or next_char.isalpha()) and \
                 (prev_char.islower() or next_char.islower()):
                return mapped_char
        elif char == "5" and mapped_char == "s":
            # 在字母上下文中纠正
            if prev_char.isdigit() and next_char.isdigit():
                return char  # 在纯数字序列中不纠正
            elif (prev_char.isalpha() or next_char.isalpha()):
                return mapped_char
        elif char == "8" and mapped_char == "s":
            # 在字母上下文中纠正
            if prev_char.isdigit() and next_char.isdigit():
                return char  # 在纯数字序列中不纠正
            elif (prev_char.isalpha() or next_char.isalpha()):
                return mapped_char
        elif char == "6" and mapped_char == "b":
            # 在字母上下文中纠正
            if prev_char.isdigit() and next_char.isdigit():
                return char  # 在纯数字序列中不纠正
            elif (prev_char.isalpha() or next_char.isalpha()):
                return mapped_char
        
        # 如果不符合上下文条件，则不进行纠正
        return char

    def get_cleaner_info(self) -> Dict[str, Any]:
        """
        获取清洗器的基本信息
        
        Returns:
            包含清洗器名称、描述等信息的字典
        """
        return {
            "name": "OCRSpecificCleaner",
            "description": "OCR专用文本清洗器，专门处理图像OCR识别结果中的格式问题",
            "features": [
                "OCR空格粘连修复",
                "OCR字符错误纠正",
                "上下文感知的错误纠正",
                "仅处理image格式元素"
            ],
            "config": {
                "fix_space_glue_errors": self.config.fix_space_glue_errors,
                "correct_ocr_errors": self.config.correct_ocr_errors,
                "merge_chinese_characters": self.config.merge_chinese_characters,
                "merge_adjacent_digits": self.config.merge_adjacent_digits,
                "merge_adjacent_letters": self.config.merge_adjacent_letters
            }
        }