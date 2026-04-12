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
