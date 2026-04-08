from pydantic import BaseModel
from typing import Optional


class Chunk(BaseModel):
    id: str
    text: str
    chapter: Optional[str] = None
    order: int = 0