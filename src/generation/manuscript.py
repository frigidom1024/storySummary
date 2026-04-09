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

    @property
    def full_manuscript(self) -> str:
        """Merge all chapter manuscripts with separators."""
        parts = []
        for i, ch in enumerate(self.chapters, 1):
            parts.append(f"第{i}章：{ch.title}\n\n{ch.manuscript}")
        return "\n\n---\n\n".join(parts)