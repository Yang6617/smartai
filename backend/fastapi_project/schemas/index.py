from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.database_models import MediaType, FileType
import datetime as dt


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: dt.datetime

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    name: str
    description: str


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    owner_id: int
    created_at: dt.datetime

    class Config:
        from_attributes = True


class FileInfoResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    upload_time: dt.datetime
    uploader_id: int
    group_id: Optional[int] = None
    file_category: str
    file_type: str

    class Config:
        from_attributes = True


class QaCreate(BaseModel):
    question: str
    media_type: MediaType = MediaType.text
    group_id: Optional[int] = None
    source_document_id: Optional[int] = None


class QaResponse(BaseModel):
    id: int
    question: str
    answer: str
    media_type: str
    user_id: int
    group_id: Optional[int] = None
    source_document_id: Optional[int] = None
    created_at: dt.datetime

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    qa_record_id: int


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    qa_record_id: int
    qa_record: QaResponse
    created_at: dt.datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class ShareToGroupRequest(BaseModel):
    qa_record_id: int
    target_group_id: int


class WeChatCodeRequest(BaseModel):
    code: str


class WeChatLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str