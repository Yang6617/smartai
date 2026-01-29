"""
文件类型识别模块

提供基于文件扩展名和二进制签名的文件类型识别功能
"""
import os
import mimetypes
from typing import Tuple, Optional
from pathlib import Path


class FileTypeIdentifier:
    """文件类型识别器"""
    
    # 常见文件类型的魔数（Magic Numbers）签名
    MAGIC_NUMBERS = {
        # 图片格式
        'image/jpeg': [(b'\xff\xd8\xff', 0)],
        'image/png': [(b'\x89PNG\r\n\x1a\n', 0)],
        'image/gif': [(b'GIF87a', 0), (b'GIF89a', 0)],
        'image/bmp': [(b'BM', 0)],
        'image/webp': [(b'RIFF', 0, b'WEBP')],
        
        # 文档格式
        'application/pdf': [(b'%PDF-', 0)],
        'application/msword': [(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 0)],  # .doc
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [(b'PK\x03\x04', 0)],  # .docx
        'application/vnd.ms-excel': [(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 0)],  # .xls
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': [(b'PK\x03\x04', 0)],  # .xlsx
        'application/vnd.ms-powerpoint': [(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 0)],  # .ppt
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': [(b'PK\x03\x04', 0)],  # .pptx
        
        # 压缩格式
        'application/zip': [(b'PK\x03\x04', 0), (b'PK\x05\x06', 0), (b'PK\x07\x08', 0)],
        'application/x-rar-compressed': [(b'Rar!\x1a\x07\x00', 0), (b'Rar!\x1a\x07\x01\x00', 0)],
        'application/x-7z-compressed': [(b'7z\xbc\xaf\x27\x1c', 0)],
        'application/gzip': [(b'\x1f\x8b', 0)],
        
        # 文本格式
        'text/plain': [(b'#!', 0)],  # 脚本文件
        'text/html': [(b'<!DOCTYPE html', 0, None, True), (b'<html', 0, None, True), (b'<HTML', 0, None, True)],
        'text/xml': [(b'<?xml', 0, None, True), (br'<\?xml', 0, None, True)],
        
        # Markdown
        'text/markdown': [('# ', 0, None, True), ('## ', 0, None, True), ('- ', 0, None, True), ('* ', 0, None, True)],
    }

    @classmethod
    def identify_file_type(cls, file_path: str) -> Tuple[str, str, float]:
        """
        识别文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            tuple: (mime_type, extension, confidence_score)
                   confidence_score: 0.0-1.0, 双重验证成功则为1.0，单一验证为0.8
        """
        # 获取文件扩展名
        ext = Path(file_path).suffix.lower()
        
        # 通过扩展名获取MIME类型
        mime_from_ext = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # 通过二进制签名检测MIME类型
        mime_from_signature = cls._detect_by_signature(file_path)
        
        # 验证两种方式的结果
        if mime_from_ext != 'application/octet-stream' and mime_from_signature and mime_from_ext == mime_from_signature:
            # 两者一致，置信度最高
            return mime_from_ext, ext, 1.0
        elif mime_from_signature:
            # 仅签名检测成功
            return mime_from_signature, ext, 0.8
        else:
            # 仅扩展名检测成功
            return mime_from_ext, ext, 0.8

    @classmethod
    def _detect_by_signature(cls, file_path: str) -> Optional[str]:
        """
        通过二进制签名检测文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIME类型字符串，如果未识别则返回None
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)  # 读取文件头32字节用于检测
                
                for mime_type, signatures in cls.MAGIC_NUMBERS.items():
                    for sig in signatures:
                        magic_bytes = sig[0]
                        offset = sig[1]
                        
                        # 检查是否有额外的中间内容（例如WEBP在RIFF之后）
                        if len(sig) >= 3:
                            middle_content = sig[2]
                        else:
                            middle_content = None
                        
                        # 检查是否需要忽略大小写
                        if len(sig) >= 4:
                            case_insensitive = sig[3]
                        else:
                            case_insensitive = False
                        
                        # 执行检测
                        if cls._match_signature(header, magic_bytes, offset, middle_content, case_insensitive):
                            return mime_type
        except Exception:
            pass
        
        return None

    @classmethod
    def _match_signature(cls, header: bytes, magic_bytes: bytes, offset: int, middle_content: Optional[bytes] = None, case_insensitive: bool = False) -> bool:
        """
        匹配文件签名
        
        Args:
            header: 文件头部数据
            magic_bytes: 魔数
            offset: 偏移量
            middle_content: 中间内容（可选）
            case_insensitive: 是否忽略大小写
            
        Returns:
            是否匹配
        """
        if len(header) < offset + len(magic_bytes):
            return False
            
        if case_insensitive:
            target = header[offset:offset+len(magic_bytes)].lower()
            magic = magic_bytes.lower()
        else:
            target = header[offset:offset+len(magic_bytes)]
            magic = magic_bytes
            
        if target.startswith(magic):
            if middle_content:
                # 检查中间内容是否存在
                pos = offset + len(magic)
                if pos + len(middle_content) <= len(header):
                    if case_insensitive:
                        return middle_content.lower() in header[pos:].lower()
                    else:
                        return middle_content in header[pos:]
            return True
        return False


# 简单测试
if __name__ == "__main__":
    import tempfile
    
    # 创建测试文件
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        f.write(b'This is a test file.')
        test_file = f.name
    
    try:
        identifier = FileTypeIdentifier()
        mime_type, ext, confidence = identifier.identify_file_type(test_file)
        print(f"文件: {test_file}")
        print(f"MIME类型: {mime_type}")
        print(f"扩展名: {ext}")
        print(f"置信度: {confidence}")
    finally:
        os.unlink(test_file)