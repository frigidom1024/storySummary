from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class BookCreate(BaseModel):
    title: str


class BookResponse(BaseModel):
    id: str
    user_id: str
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    cover_url: Optional[str] = None
    status: str
    nodes_file_path: str
    created_at: datetime

    class Config:
        from_attributes = True


class NodesResponse(BaseModel):
    book_id: str
    structure: Optional[dict] = None
    nodes: List[dict] = []


class SaveNodesRequest(BaseModel):
    structure: Optional[dict] = None
    nodes: List[dict] = []


class ManuscriptRequest(BaseModel):
    """口播稿生成请求"""
    style_key: Optional[str] = None  # 预设风格：轻松聊天、深度解读、故事讲述、专业评论
    custom_rules: Optional[str] = None  # 自定义规则
    reference_script: Optional[str] = None  # 参考口播稿


class ManuscriptResponse(BaseModel):
    """口播稿生成响应"""
    book_id: str
    title: str
    phase: str
    chapters_written: int
    total_chunks: int
    manuscript: str
