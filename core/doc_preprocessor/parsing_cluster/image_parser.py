"""
简化版图片文档解析器
使用PaddleOCR将图片中的文本内容解析为Element对象列表
此版本简化了初始化参数以避免兼容性问题
"""

import os
from typing import Dict, Any, List
from pathlib import Path
import cv2
import numpy as np

from .processor import DocumentParser, ParseResult, Element
from .config import DocPreprocessorConfig


class ImageParser(DocumentParser):
    """图片文档解析器"""
    
    def __init__(self, config: DocPreprocessorConfig = None):
        self.config = config or DocPreprocessorConfig()
        # 延迟初始化OCR引擎，避免启动时加载模型
        self._ocr = None
    
    @property
    def ocr(self):
        """懒加载PaddleOCR实例"""
        if self._ocr is None:
            try:
                import os
                # 设置环境变量以解决PIR兼容性问题
                os.environ['ENABLE_PIR'] = '0'
                
                from paddleocr import PaddleOCR
                # 使用最基本的配置以避免兼容性问题
                self._ocr = PaddleOCR(use_angle_cls=True, lang="ch")
            except ImportError:
                raise ImportError("请先安装PaddleOCR: pip install paddleocr")
            except Exception as e:
                print(f"初始化PaddleOCR时出错: {e}")
                raise
        return self._ocr
    
    def parse(self, file_path: str, user_id: str, knowledge_base_id: str) -> Dict[str, Any]:
        """
        解析图片文档
        
        Args:
            file_path: 图片文件路径（来自用户上传）
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
        elements = self._parse_image(file_path)
        
        result = ParseResult(
            user_id=user_id,
            file_name=Path(file_path).name,
            knowledge_base_id=knowledge_base_id,
            elements=elements
        )
        
        return result.to_dict()
    
    def _parse_image(self, file_path: str) -> List[Element]:
        """
        解析图片内容为Element列表
        """
        elements = []
        element_index = 0
        
        try:
            # 使用PaddleOCR进行文本识别
            result = self.ocr.ocr(file_path)
            
            if result is None or len(result) == 0:
                # 如果没有识别到任何内容，返回空列表
                return elements
            
            # 解析OCR结果
            ocr_result = result[0]  # 获取第一个结果（单张图片）
            
            for idx, (bbox, (text, confidence)) in enumerate(ocr_result):
                # 为每个识别到的文本区域创建Element
                element = self._create_text_region_element(
                    text=text,
                    bbox=bbox,
                    confidence=confidence,
                    element_index=element_index
                )
                elements.append(element)
                element_index += 1
            
            # 尝试检测表格区域（如果有的话）
            table_elements = self._detect_tables(file_path)
            for table_element in table_elements:
                table_element.element_index = element_index
                elements.append(table_element)
                element_index += 1
        
        except Exception as e:
            print(f"OCR处理图片时出错: {e}")
            # 即使出错也要返回基本的元素结构
            error_element = Element(
                raw_content=f"图片解析失败: {str(e)}",
                element_type="error",
                element_index=element_index,
                source_format="image",
                format_metadata={
                    "detected_language": "unknown",
                    "character_count": len(f"图片解析失败: {str(e)}"),
                    "is_structural": False
                },
                parser_confidence=0.0
            )
            elements.append(error_element)
        
        return elements
    
    def _create_text_region_element(self, text: str, bbox: List[List[float]], 
                                  confidence: float, element_index: int) -> Element:
        """创建文本区域Element"""
        # bbox格式通常是 [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        bbox_rect = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        
        metadata = {
            "bbox": [int(coord) for coord in bbox_rect],  # 转换为整数坐标
            "ocr_confidence": round(float(confidence), 3),
            "font_attributes": {},  # PaddleOCR不直接提供字体信息
            "text_direction": "horizontal",  # 默认水平方向
            "detected_language": "zh-CN",
            "character_count": len(text),
            "is_structural": False
        }
        
        element = Element(
            raw_content=text,
            element_type="text_region",
            element_index=element_index,
            source_format="image",
            format_metadata=metadata,
            parser_confidence=min(1.0, max(0.0, float(confidence)))  # 确保置信度在0-1之间
        )
        
        return element
    
    def _detect_tables(self, file_path: str) -> List[Element]:
        """检测图片中的表格区域（简化实现，可以根据需求增强）"""
        # 这里是简化实现，实际应用中可以集成表格识别模型
        # 目前我们只是检查是否有可能的表格文本
        elements = []
        
        # 尝试使用OCR结果识别表格相关文本
        # 这是一个简化的实现，实际中可能需要专门的表格识别模型
        try:
            result = self.ocr.ocr(file_path)
            
            if result is None or len(result) == 0:
                return elements
            
            ocr_result = result[0]
            
            # 检查是否包含可能的表格相关词汇
            table_keywords = ["表", "表格", "统计", "数据", "对比", "清单", "明细"]
            
            for idx, (bbox, (text, confidence)) in enumerate(ocr_result):
                # 如果文本包含表格关键词，则创建表格元素
                if any(keyword in text for keyword in table_keywords):
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    bbox_rect = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                    
                    metadata = {
                        "bbox": [int(coord) for coord in bbox_rect],
                        "cell_count": {"rows": 0, "cols": 0},  # 表格行列数需要进一步分析
                        "has_border": True,  # 假设包含表格关键词的区域是有边框的
                        "detected_language": "zh-CN",
                        "character_count": len(text),
                        "is_structural": True
                    }
                    
                    element = Element(
                        raw_content=text,
                        element_type="table_region",
                        element_index=-1,  # 临时index，后面会重新设置
                        source_format="image",
                        format_metadata=metadata,
                        parser_confidence=min(1.0, max(0.0, float(confidence)))
                    )
                    elements.append(element)
        except:
            pass  # 忽略表格检测错误
        
        return elements
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的图片格式"""
        return ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']


def main():
    """主函数 - 演示如何使用图片解析器"""
    config = DocPreprocessorConfig()
    parser = ImageParser(config)
    
    print("支持的图片格式:", parser.get_supported_formats())


if __name__ == "__main__":
    main()