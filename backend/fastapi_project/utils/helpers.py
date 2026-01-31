from pathlib import Path
from models.database_models import FileType


def determine_file_type(filename: str) -> FileType:
    """根据文件扩展名判断文件类型"""
    ext = Path(filename).suffix.lower()
    if ext in ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx']:
        return FileType.document
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
        return FileType.image
    elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']:
        return FileType.video
    elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
        return FileType.audio
    else:
        return FileType.other