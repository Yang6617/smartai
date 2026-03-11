"""
智能分块引擎主类
整合语义边界检测、自适应分块和重叠控制功能
"""
from typing import List, Dict, Any, Optional
from .boundary_detector.detector import BoundaryDetectorFactory, Boundary
from .adaptive_chunker.chunker import AdaptiveChunkerFactory, ChunkConfig
from .overlap_controller.controller import OverlapControllerFactory
from .chunk import Chunk, format_chunks_for_output, ChunkType
from ..parsing_cluster.processor import Element


class SmartChunkingEngine:
    """
    智能分块引擎
    整合语义边界检测、自适应分块和重叠控制功能
    """
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
        
        # 初始化各组件
        self.boundary_detector_factory = BoundaryDetectorFactory()
        self.adaptive_chunker_factory = AdaptiveChunkerFactory()
        self.overlap_controller_factory = OverlapControllerFactory()
    
    def chunk_elements(self, 
                      elements: List[Element], 
                      document_id: str, 
                      team_id: str, 
                      user_id: str, 
                      file_name: str, 
                      file_type: str,
                      overlap_size: int = 50,
                      structure_path: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        对Element列表进行智能分块
        
        Args:
            elements: Element对象列表
            document_id: 文档ID
            team_id: 团队ID
            user_id: 用户ID
            file_name: 文件名
            file_type: 文件类型
            overlap_size: 重叠大小
            structure_path: 结构路径（如标题层级）
            
        Returns:
            格式化的分块结果
        """
        # 预处理：将子标题的内容合并到父标题中
        merged_elements = self._merge_child_content_to_parent(elements)
        
        all_chunks = []
        
        for element in merged_elements:
            element_chunks = self._process_element(
                element=element,
                file_type=file_type,
                overlap_size=overlap_size,
                structure_path=structure_path or []
            )
            all_chunks.extend(element_chunks)
        
        # 转换为Chunk对象
        chunk_objects = []
        for idx, chunk_data in enumerate(all_chunks):
            chunk_obj = Chunk(
                text=chunk_data["text"],
                chunk_index=idx,
                structure_path=chunk_data.get("structure_path"),
                element_type=chunk_data.get("element_type"),
                chunk_type=self._get_chunk_type_from_element_type(chunk_data.get("element_type")),
                metadata=chunk_data.get("metadata"),
                format_metadata=chunk_data.get("format_metadata"),
                overlap_info=chunk_data.get("overlap_info"),
                confidence=chunk_data.get("confidence", 1.0)
            )
            chunk_objects.append(chunk_obj)
        
        # 格式化输出
        return format_chunks_for_output(
            chunks=chunk_objects,
            document_id=document_id,
            team_id=team_id,
            user_id=user_id,
            file_name=file_name,
            file_type=file_type
        )
    
    def _merge_child_content_to_parent(self, elements: List[Element]) -> List[Element]:
        """
        将子标题的内容合并到父标题中
        
        Args:
            elements: Element对象列表
            
        Returns:
            合并后的Element对象列表
        """
        if not elements:
            return elements
        
        merged_elements = []
        i = 0
        
        while i < len(elements):
            current_element = elements[i]
            
            # 如果当前Element是标题，检查是否有子标题
            if current_element.element_type == "heading":
                heading_level = current_element.format_metadata.get("heading_level", 0)
                
                # 收集后续的子标题和内容
                child_content_parts = []
                j = i + 1
                
                while j < len(elements):
                    next_element = elements[j]
                    next_heading_level = next_element.format_metadata.get("heading_level", 0)
                    
                    # 如果下一个Element是子标题（层级更深的标题）
                    if next_element.element_type == "heading" and next_heading_level > heading_level:
                        # 收集子标题的内容
                        child_content_parts.append(next_element.raw_content)
                        j += 1
                    # 如果下一个Element是列表项，也收集到父标题中
                    elif next_element.element_type == "list_item":
                        child_content_parts.append(next_element.raw_content)
                        j += 1
                    # 如果下一个Element是段落，也收集到父标题中
                    elif next_element.element_type == "paragraph":
                        child_content_parts.append(next_element.raw_content)
                        j += 1
                    else:
                        # 如果层级不更深，说明已经离开当前标题的范围
                        break
                
                # 如果有子标题内容，将它们添加到当前标题的chunks中
                if child_content_parts:
                    # 创建新的Element，包含子标题内容
                    new_element = Element(
                        raw_content=current_element.raw_content + "\n\n" + "\n".join(child_content_parts),
                        element_type=current_element.element_type,
                        element_index=current_element.element_index,
                        source_format=current_element.source_format,
                        format_metadata=current_element.format_metadata.copy(),
                        parser_confidence=current_element.parser_confidence
                    )
                    merged_elements.append(new_element)
                else:
                    merged_elements.append(current_element)
                
                i = j
            else:
                merged_elements.append(current_element)
                i += 1
        
        return merged_elements
    
    def _process_element(self, 
                        element: Element, 
                        file_type: str, 
                        overlap_size: int, 
                        structure_path: List[str]) -> List[Dict[str, Any]]:
        """
        处理单个Element对象
        
        Args:
            element: Element对象
            file_type: 文件类型
            overlap_size: 重叠大小
            structure_path: 结构路径
            
        Returns:
            分块结果列表
        """
        # 获取对应的分块器
        chunker = self.adaptive_chunker_factory.get_chunker(element.element_type)
        
        # 执行分块
        raw_chunks = chunker.chunk(
            text=element.raw_content,
            element_type=element.element_type,
            file_type=file_type,
            config=self.config
        )
        
        # 应用重叠控制
        overlap_controller = self.overlap_controller_factory.get_controller("simple")
        overlapped_chunks = overlap_controller.apply_overlap(raw_chunks, overlap_size)
        
        # 添加结构路径和其他元数据
        processed_chunks = []
        for chunk_data in overlapped_chunks:
            # 优先使用Element自带的结构路径，如果没有则使用传入的默认路径
            element_structure_path = element.format_metadata.get("structure_path", structure_path)
            
            processed_chunk = {
                "text": chunk_data.get("text_with_overlap", chunk_data["text"]),
                "element_type": element.element_type,
                "structure_path": element_structure_path,
                "metadata": chunk_data.get("metadata", {}),
                "format_metadata": element.format_metadata,
                "overlap_info": {
                    "prefix": chunk_data.get("overlap_prefix", ""),
                    "suffix": chunk_data.get("overlap_suffix", ""),
                    "has_overlap": bool(chunk_data.get("overlap_prefix"))
                },
                "confidence": element.parser_confidence
            }
            processed_chunks.append(processed_chunk)
        
        return processed_chunks
    
    def _get_chunk_type_from_element_type(self, element_type: str) -> Optional[ChunkType]:
        """
        根据Element类型推断Chunk类型
        
        Args:
            element_type: Element类型
            
        Returns:
            对应的ChunkType
        """
        if not element_type:
            return ChunkType.TEXT
            
        element_type_lower = element_type.lower()
        
        if "code" in element_type_lower or "block" in element_type_lower:
            return ChunkType.CODE
        elif "table" in element_type_lower:
            return ChunkType.TABLE
        elif "list" in element_type_lower:
            return ChunkType.LIST
        elif "heading" in element_type_lower or "header" in element_type_lower:
            return ChunkType.HEADING
        else:
            return ChunkType.TEXT
    
    def chunk_text_with_structure_detection(self, 
                                          text: str, 
                                          file_type: str, 
                                          document_id: str, 
                                          team_id: str, 
                                          user_id: str, 
                                          file_name: str,
                                          overlap_size: int = 50) -> Dict[str, Any]:
        """
        对文本进行带结构检测的分块
        自动检测文档结构（如Markdown标题）并维护层级关系
        
        Args:
            text: 待分块的文本
            file_type: 文件类型
            document_id: 文档ID
            team_id: 团队ID
            user_id: 用户ID
            file_name: 文件名
            overlap_size: 重叠大小
            
        Returns:
            格式化的分块结果
        """
        # 检测语义边界
        detector = self.boundary_detector_factory.get_detector(file_type)
        boundaries = detector.detect_boundaries(text, file_type)
        
        # 根据边界信息创建结构路径
        structure_info = self._analyze_structures(boundaries, text)
        
        # 将文本按结构切分
        structured_elements = self._create_structured_elements(text, boundaries, structure_info)
        
        # 对每个结构化元素进行分块
        all_chunks = []
        for struct_elem in structured_elements:
            element_chunks = self._process_element(
                element=struct_elem,
                file_type=file_type,
                overlap_size=overlap_size,
                structure_path=struct_elem.format_metadata.get("structure_path", [])
            )
            all_chunks.extend(element_chunks)
        
        # 转换为Chunk对象
        chunk_objects = []
        for idx, chunk_data in enumerate(all_chunks):
            chunk_obj = Chunk(
                text=chunk_data["text"],
                chunk_index=idx,
                structure_path=chunk_data.get("structure_path"),
                element_type=chunk_data.get("element_type"),
                chunk_type=self._get_chunk_type_from_element_type(chunk_data.get("element_type")),
                metadata=chunk_data.get("metadata"),
                overlap_info=chunk_data.get("overlap_info"),
                confidence=chunk_data.get("confidence", 1.0)
            )
            chunk_objects.append(chunk_obj)
        
        # 格式化输出
        return format_chunks_for_output(
            chunks=chunk_objects,
            document_id=document_id,
            team_id=team_id,
            user_id=user_id,
            file_name=file_name,
            file_type=file_type
        )
    
    def _analyze_structures(self, boundaries: List[Boundary], text: str) -> Dict[str, Any]:
        """
        分析文档结构，建立标题层级关系
        
        Args:
            boundaries: 边界列表
            text: 原始文本
            
        Returns:
            结构分析结果
        """
        from .boundary_detector.detector import BoundaryType
        
        structure_info = {
            "headings": [],
            "positions_to_headings": {},  # 位置到标题的映射
            "hierarchy": {}
        }
        
        current_path = []
        
        for boundary in boundaries:
            if boundary.type == BoundaryType.HEADING and boundary.metadata:
                level = boundary.metadata.get("level", 1)
                title = boundary.metadata.get("title", "")
                
                # 维护标题层级
                while len(current_path) >= level:
                    if current_path:
                        current_path.pop()
                
                # 添加当前标题到路径
                heading_str = f"{'#' * level} {title}"
                current_path = current_path[:level-1]  # 保留父级标题
                current_path.append(heading_str)
                
                structure_info["headings"].append({
                    "level": level,
                    "title": title,
                    "position": boundary.position,
                    "path": current_path[:]
                })
                
                # 记录每个位置对应的标题路径
                structure_info["positions_to_headings"][boundary.position] = current_path[:]
        
        structure_info["current_path"] = current_path
        return structure_info
    
    def _create_structured_elements(self, text: str, boundaries: List[Boundary], structure_info: Dict[str, Any]) -> List[Element]:
        """
        根据边界和结构信息创建结构化Element对象
        
        Args:
            text: 原始文本
            boundaries: 边界列表
            structure_info: 结构信息
            
        Returns:
            结构化Element对象列表
        """
        from .boundary_detector.detector import BoundaryType
        
        elements = []
        
        # 如果没有边界，将整个文本作为一个元素
        if not boundaries:
            elements.append(Element(
                raw_content=text,
                element_type="paragraph",
                element_index=0,
                source_format="structured_text",
                format_metadata={"structure_path": []},
                parser_confidence=1.0
            ))
            return elements
        
        # 按位置排序边界
        sorted_boundaries = sorted(boundaries, key=lambda x: x.position)
        
        # 根据边界分割文本
        start_pos = 0
        element_index = 0
        
        for boundary in sorted_boundaries:
            # 获取当前位置到边界之间的文本
            if boundary.position > start_pos:
                content = text[start_pos:boundary.position]
                if content.strip():
                    # 确定当前内容的结构路径
                    current_path = self._get_structure_path_for_position(start_pos, structure_info)
                    
                    elements.append(Element(
                        raw_content=content,
                        element_type=self._infer_element_type(content),
                        element_index=element_index,
                        source_format="structured_text",
                        format_metadata={"structure_path": current_path},
                        parser_confidence=0.9
                    ))
                    element_index += 1
            
            # 处理边界本身（如标题）
            if boundary.type == BoundaryType.HEADING:
                # 提取标题行
                end_of_line = text.find('\n', boundary.position)
                if end_of_line == -1:
                    end_of_line = len(text)
                heading_text = text[boundary.position:end_of_line]
                
                # 获取标题的结构路径（包括自身）
                heading_path = boundary.metadata.get("path", [])
                
                elements.append(Element(
                    raw_content=heading_text,
                    element_type="heading",
                    element_index=element_index,
                    source_format="structured_text",
                    format_metadata={"structure_path": heading_path},
                    parser_confidence=1.0
                ))
                element_index += 1
            
            # 更新起始位置
            start_pos = end_of_line if boundary.type == BoundaryType.HEADING else boundary.position
        
        # 添加最后剩余的文本
        if start_pos < len(text):
            content = text[start_pos:]
            if content.strip():
                # 确定最后内容的结构路径
                current_path = self._get_structure_path_for_position(start_pos, structure_info)
                
                elements.append(Element(
                    raw_content=content,
                    element_type="paragraph",
                    element_index=element_index,
                    source_format="structured_text",
                    format_metadata={"structure_path": current_path},
                    parser_confidence=0.9
                ))
        
        return elements
    
    def _get_structure_path_for_position(self, position: int, structure_info: Dict[str, Any]) -> List[str]:
        """
        为指定位置获取最接近的结构路径
        
        Args:
            position: 文本位置
            structure_info: 结构信息
            
        Returns:
            结构路径列表
        """
        # 找到在指定位置之前的最近标题
        closest_heading = None
        for heading in structure_info["headings"]:
            if heading["position"] <= position:
                if closest_heading is None or heading["position"] > closest_heading["position"]:
                    closest_heading = heading
        
        if closest_heading:
            return closest_heading["path"][:]
        else:
            return []
    
    def _infer_element_type(self, content: str) -> str:
        """
        推断元素类型
        
        Args:
            content: 内容文本
            
        Returns:
            推断的元素类型
        """
        content_lower = content.lower().strip()
        
        # 检查是否为代码块
        if "```" in content or "\n    " in content or "\n\t" in content:
            return "code_block"
        
        # 检查是否为表格（以|分隔的行）
        lines = content.split('\n')
        table_lines = [line for line in lines if line.strip().startswith('|')]
        if len(table_lines) > 1:
            return "table"
        
        # 检查是否为列表
        list_patterns = [r'^\s*[*+-]\s+', r'^\s*\d+\.\s+']
        import re
        for pattern in list_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return "list_item"
        
        # 默认为段落
        return "paragraph"