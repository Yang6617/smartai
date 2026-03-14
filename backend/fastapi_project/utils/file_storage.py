from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
import os
import shutil


class FileStorage(ABC):
    """文件存储抽象基类"""
    
    @abstractmethod
    def save_file(self, file_data: bytes, filename: str, group_id: Optional[int] = None) -> str:
        """
        保存文件
        :param file_data: 文件二进制数据
        :param filename: 原始文件名
        :param group_id: 群组ID，用于组织文件目录结构
        :return: 存储路径或标识符
        """
        pass

    @abstractmethod
    def load_file(self, storage_path: str) -> bytes:
        """
        加载文件
        :param storage_path: 存储路径或标识符
        :return: 文件二进制数据
        """
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """
        删除文件
        :param storage_path: 存储路径或标识符
        :return: 是否删除成功
        """
        pass

    @abstractmethod
    def get_file_path(self, storage_path: str) -> str:
        """
        获取文件的系统路径
        :param storage_path: 存储路径或标识符
        :return: 系统路径
        """
        pass


class LocalFileStorage(FileStorage):
    """本地文件存储实现"""
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _get_group_directory(self, group_id: int) -> Path:
        """获取群组目录路径"""
        # 群组文件存放在 group_{id} 目录下
        group_dir = self.base_path / f"group_{group_id}"
        group_dir.mkdir(exist_ok=True)
        return group_dir

    def save_file(self, file_data: bytes, filename: str, group_id: Optional[int] = None) -> str:
        """保存文件到对应群组目录"""
        group_dir = self._get_group_directory(group_id)
        
        # 使用原文件名保存（去除UUID前缀）
        # filename 格式: "uuid_original_filename"，我们需要提取 original_filename
        parts = filename.split('_', 1)
        if len(parts) == 2 and len(parts[0]) == 36:  # UUID长度为36
            original_filename = parts[1]
        else:
            original_filename = filename
        
        file_path = group_dir / original_filename
        counter = 1
        
        # 如果文件已存在，则添加编号
        original_stem = file_path.stem
        original_suffix = file_path.suffix
        
        while file_path.exists():
            new_filename = f"{original_stem}_{counter}{original_suffix}"
            file_path = group_dir / new_filename
            counter += 1
        
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        # 返回相对路径，用于在数据库中存储
        return str(file_path.relative_to(self.base_path))

    def load_file(self, storage_path: str) -> bytes:
        """从存储中加载文件"""
        file_path = self.base_path / storage_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file(self, storage_path: str) -> bool:
        """删除文件"""
        file_path = self.base_path / storage_path
        if file_path.exists():
            try:
                file_path.unlink()
                # 尝试删除空的父目录
                parent_dir = file_path.parent
                if parent_dir != self.base_path and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                return True
            except OSError:
                return False
        return False

    def get_file_path(self, storage_path: str) -> str:
        """获取文件的系统路径"""
        return str(self.base_path / storage_path)