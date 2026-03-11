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
            
            # 对文本区域按垂直位置排序（从上到下，从左到右）
            sorted_regions = self._sort_text_regions(ocr_result)
            
            # 检测表格区域
            table_regions = self._detect_table_regions(sorted_regions)
            
            # 标题栈，用于跟踪当前的标题层级
            heading_stack = []
            
            # 处理每个文本区域
            for idx, (bbox, (text, confidence)) in enumerate(sorted_regions):
                # 检查是否属于表格区域
                is_table = any(self._is_region_in_table(bbox, table_region) 
                              for table_region in table_regions)
                
                # 检查是否为标题
                is_title = self._is_title(text)
                
                # 构建structure_path
                structure_path = [h['title'] for h in heading_stack]
                
                # 如果是标题，更新标题栈
                if is_title:
                    # 解析标题层级
                    heading_level = self._get_heading_level(text)
                    
                    # 更新标题栈
                    # 只有当新标题的层级大于当前标题时，才弹出当前标题
                    # 例如：从"1."到"2."时弹出"1."，从"3.1"到"3.2"时弹出"3.1"
                    while heading_stack and heading_stack[-1]['level'] > heading_level:
                        heading_stack.pop()
                    
                    # 添加当前标题
                    heading_stack.append({
                        'level': heading_level,
                        'title': text
                    })
                    
                    # 重新构建structure_path
                    structure_path = [h['title'] for h in heading_stack]
                
                # 为每个识别到的文本区域创建Element
                element = self._create_text_region_element(
                    text=text,
                    bbox=bbox,
                    confidence=confidence,
                    element_index=element_index,
                    is_table_region=is_table,
                    structure_path=structure_path,
                    is_title=is_title
                )
                elements.append(element)
                element_index += 1
            
            # 添加表格区域作为单独的Element
            for table_region in table_regions:
                table_element = self._create_table_element(
                    table_region=table_region,
                    element_index=element_index
                )
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
    
    def _sort_text_regions(self, ocr_result):
        """按垂直位置排序文本区域（从上到下，从左到右）"""
        if not ocr_result:
            return []
        
        regions = []
        for bbox, (text, confidence) in ocr_result:
            # 计算文本区域的中心点
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            center_y = sum(y_coords) / len(y_coords)
            center_x = sum(x_coords) / len(x_coords)
            
            regions.append({
                'bbox': bbox,
                'text': text,
                'confidence': confidence,
                'center_y': center_y,
                'center_x': center_x,
                'y_top': min(y_coords)
            })
        
        # 按垂直位置排序（从上到下）
        # 对于同一行的文本，按水平位置排序（从左到右）
        regions.sort(key=lambda r: (r['y_top'], r['center_x']))
        
        return [(r['bbox'], (r['text'], r['confidence'])) for r in regions]
    
    def _detect_table_regions(self, sorted_regions):
        """检测表格区域"""
        table_regions = []
        
        if len(sorted_regions) < 4:  # 表格至少需要几个单元格
            return table_regions
        
        # 简单的表格检测：查找具有相似垂直位置的文本区域
        # 将文本区域按垂直位置分组
        y_tolerance = 20  # 垂直位置容差
        groups = []
        current_group = []
        
        for bbox, (text, confidence) in sorted_regions:
            y_coords = [point[1] for point in bbox]
            center_y = sum(y_coords) / len(y_coords)
            
            if not current_group:
                current_group.append((bbox, text, center_y))
            else:
                # 检查是否与当前组在同一行
                if abs(center_y - current_group[0][2]) < y_tolerance:
                    current_group.append((bbox, text, center_y))
                else:
                    # 开始新组
                    if len(current_group) >= 2:  # 至少2个单元格才认为是表格行
                        groups.append(current_group)
                    current_group = [(bbox, text, center_y)]
        
        # 添加最后一组
        if len(current_group) >= 2:
            groups.append(current_group)
        
        # 检查是否有多个行组（表格）
        if len(groups) >= 2:
            # 合并所有表格区域
            all_bboxes = []
            for group in groups:
                for bbox, text, center_y in group:
                    all_bboxes.append(bbox)
            
            # 计算表格的边界框
            x_coords = []
            y_coords = []
            for bbox in all_bboxes:
                x_coords.extend([point[0] for point in bbox])
                y_coords.extend([point[1] for point in bbox])
            
            table_bbox = [
                [min(x_coords), min(y_coords)],
                [max(x_coords), min(y_coords)],
                [max(x_coords), max(y_coords)],
                [min(x_coords), max(y_coords)]
            ]
            
            table_regions.append({
                'bbox': table_bbox,
                'rows': len(groups),
                'cols': max(len(g) for g in groups),
                'cells': all_bboxes
            })
        
        return table_regions
    
    def _is_region_in_table(self, region_bbox, table_region):
        """检查文本区域是否在表格区域内"""
        table_bbox = table_region['bbox']
        
        # 计算区域的边界框
        region_x_coords = [point[0] for point in region_bbox]
        region_y_coords = [point[1] for point in region_bbox]
        region_rect = [min(region_x_coords), min(region_y_coords), 
                      max(region_x_coords), max(region_y_coords)]
        
        table_x_coords = [point[0] for point in table_bbox]
        table_y_coords = [point[1] for point in table_bbox]
        table_rect = [min(table_x_coords), min(table_y_coords), 
                     max(table_x_coords), max(table_y_coords)]
        
        # 检查区域是否在表格边界框内
        return (region_rect[0] >= table_rect[0] and 
                region_rect[1] >= table_rect[1] and 
                region_rect[2] <= table_rect[2] and 
                region_rect[3] <= table_rect[3])
    
    def _create_table_element(self, table_region, element_index):
        """创建表格Element"""
        bbox = table_region['bbox']
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        bbox_rect = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        
        metadata = {
            "bbox": [int(coord) for coord in bbox_rect],
            "table_rows": table_region.get('rows', 0),
            "table_cols": table_region.get('cols', 0),
            "cell_count": len(table_region.get('cells', [])),
            "detected_language": "zh-CN",
            "is_structural": True
        }
        
        element = Element(
            raw_content=f"表格区域: {metadata['table_rows']}行 x {metadata['table_cols']}列",
            element_type="table",
            element_index=element_index,
            source_format="image",
            format_metadata=metadata,
            parser_confidence=0.9
        )
        
        return element
    
    def _get_heading_level(self, text: str) -> int:
        """获取标题层级"""
        import re
        
        # 检测Markdown标题格式（#开头）
        if text.startswith('#'):
            return len(text.split()[0])
        
        # 检测数字编号格式（如"1.", "2.1", "3.2.3"等）
        match = re.match(r'^(\d+(?:\.\d+)*)', text)
        if match:
            level = len(match.group(1).split('.'))
            return min(level, 6)
        
        return 1
    
    def _create_text_region_element(self, text: str, bbox: List[List[float]], 
                                  confidence: float, element_index: int, 
                                  is_table_region: bool = False,
                                  structure_path: List[str] = None,
                                  is_title: bool = None) -> Element:
        """创建文本区域Element"""
        # bbox格式通常是 [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        bbox_rect = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        
        # 如果is_title未提供，检测是否为标题
        if is_title is None:
            is_title = self._is_title(text)
        
        # 如果structure_path未提供，使用空列表
        if structure_path is None:
            structure_path = []
        
        metadata = {
            "bbox": [int(coord) for coord in bbox_rect],  # 转换为整数坐标
            "ocr_confidence": round(float(confidence), 3),
            "font_attributes": {},  # PaddleOCR不直接提供字体信息
            "text_direction": "horizontal",  # 默认水平方向
            "detected_language": "zh-CN",
            "character_count": len(text),
            "is_structural": is_title,
            "structure_path": structure_path
        }
        
        element = Element(
            raw_content=text,
            element_type="heading" if is_title else "text_region",
            element_index=element_index,
            source_format="image",
            format_metadata=metadata,
            parser_confidence=min(1.0, max(0.0, float(confidence)))  # 确保置信度在0-1之间
        )
        
        return element
    
    def _is_title(self, text: str) -> bool:
        """检测文本是否为标题"""
        if not text:
            return False
        
        # 检测是否包含数字编号（如"1.", "2.1", "3.2.3"等）
        import re
        if re.match(r'^\d+[\.\d]*\s*[\u4e00-\u9fa5]', text):
            return True
        
        # 检测是否包含"第X部分"等模式
        if re.match(r'^第[\d一二三四五六七八九十]+[章节部分]', text):
            return True
        
        # 检测是否为短标题（通常标题较短）
        if len(text) <= 20 and re.match(r'^[\d\w\u4e00-\u9fa5]+[.\s]*[\u4e00-\u9fa5]+$', text):
            return True
        
        return False
    
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