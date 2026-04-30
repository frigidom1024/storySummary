from pydantic import BaseModel
from typing import Optional, List


class Chunk(BaseModel):
    id: str
    text: str
    chapter: Optional[str] = None
    order: int = 0
    content_type: Optional[str] = None  # story_content / appendix / author_intro / other

    def to_dict(self) -> dict:
        """序列化为字典"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        """从字典反序列化"""
        return cls.model_validate(data)

    @classmethod
    def from_list(cls, data_list: List[dict]) -> List["Chunk"]:
        """从字典列表反序列化"""
        return [cls.model_validate(item) for item in data_list]