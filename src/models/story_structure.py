from pydantic import BaseModel, Field
from typing import Optional


class StoryStructure(BaseModel):
    linear_mainline: list[str] = Field(default_factory=list)  # node IDs in order
    opening: list[str] = Field(default_factory=list)
    rising: list[str] = Field(default_factory=list)
    climax: list[str] = Field(default_factory=list)
    ending: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return self.model_dump()