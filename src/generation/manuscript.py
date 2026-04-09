from pydantic import BaseModel
from typing import Optional


class ChapterManuscript(BaseModel):
    """Single chapter of a podcast manuscript."""
    chunk_id: str
    title: str
    manuscript: str  # full chapter text


class PodcastManuscript(BaseModel):
    """Complete podcast manuscript."""
    title: str
    author: str = ""
    estimated_duration: str = ""  # e.g., "25分钟"
    chapters: list[ChapterManuscript] = []
    full_manuscript: str = ""  # polished full manuscript

    def __init__(self, **data):
        super().__init__(**data)
        # If full_manuscript is empty but chapters exist, build from chapters
        if not self.full_manuscript and self.chapters:
            parts = []
            for i, ch in enumerate(self.chapters, 1):
                parts.append(f"第{i}章：{ch.title}\n\n{ch.manuscript}")
            object.__setattr__(self, 'full_manuscript', "\n\n---\n\n".join(parts))