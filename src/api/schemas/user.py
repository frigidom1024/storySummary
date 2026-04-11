from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    profile: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True
