from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from pydantic import BaseModel
from typing import Optional, List
import datetime
from enum import Enum
from database.db_config import Base


class MediaType(str, Enum):
    text = "text"
    image = "image"
    audio = "audio"


class FileType(str, Enum):
    document = "document"
    image = "image"
    video = "video"
    audio = "audio"
    other = "other"


# 用户模型
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# 群组模型
class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    owner = relationship("User")
    members = relationship("GroupMember", back_populates="group")
    files = relationship("FileInfo", back_populates="group")


# 群组成员关系模型
class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, default="member")  # 用户角色：admin（管理员）或 member（普通用户）
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    group = relationship("Group", back_populates="members")
    user = relationship("User")
    
    @property
    def username(self):
        return self.user.username if self.user else ""


# 文件信息模型
class FileInfo(Base):
    __tablename__ = "file_info"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    original_filename = Column(String)
    file_size = Column(Integer)
    content_type = Column(String)
    upload_time = Column(DateTime, default=datetime.datetime.utcnow)
    uploader_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)  # 必须关联群组（知识库）
    file_category = Column(String, default="general")  # 文件分类
    file_type = Column(String, default=FileType.other)  # 文件类型
    
    # 关系
    uploader = relationship("User")
    group = relationship("Group", back_populates="files")


# 问答记录模型
class QaRecord(Base):
    __tablename__ = "qa_records"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    media_type = Column(String, default="text")
    user_id = Column(Integer, ForeignKey("users.id"))
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)  # 必须关联群组（知识库）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    source_document_id = Column(Integer, ForeignKey("file_info.id"), nullable=True)  # 来源文档ID
    
    # 关系
    user = relationship("User")
    group = relationship("Group")
    source_document = relationship("FileInfo")  # 问答来源文档


# 收藏记录模型
class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    qa_record_id = Column(Integer, ForeignKey("qa_records.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关系
    user = relationship("User")
    qa_record = relationship("QaRecord")