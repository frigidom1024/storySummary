from pydantic import BaseModel, Field
from typing import Optional, List


class Chunk(BaseModel):
    id: str
    text: str
    chapter: Optional[str] = None
    order: int = 0
    content_type: Optional[str] = None  # story_content / appendix / author_intro / other

    # agent3_interesting_finder.py 中负责维护的扩展字段
    discussion_prompts: list[str] = Field(default_factory=list, description="Discussion anchors for podcast")

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