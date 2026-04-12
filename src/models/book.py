from pydantic import BaseModel
from datetime import datetime


class Book(BaseModel):
    """Book index model"""
    id: str
    user_id: str
    title: str
    author: str | None = None
    publisher: str | None = None
    cover_url: str | None = None
    nodes_file_path: str
    status: str = "pending"  # pending | processing | completed | failed
    message: str = ""  # 存储分析消息/错误信息
    is_deleted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True