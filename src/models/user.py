from pydantic import BaseModel
from datetime import datetime


class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: str
    password_hash: str
    profile: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True