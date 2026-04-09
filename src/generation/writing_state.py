from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import json
from pathlib import Path


class WritingPhase(str, Enum):
    PLANNING = "planning"
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"


class ChapterOutline(BaseModel):
    chunk_id: str
    title: str
    summary: str = ""


class WrittenChapter(BaseModel):
    chunk_id: str
    manuscript: str


class WritingState(BaseModel):
    """State file for PodcastWritingAgent checkpoint/resume."""
    book_title: str
    phase: WritingPhase = WritingPhase.PLANNING
    current_chunk_index: int = 0

    # Phase 1 output
    outline: Optional[dict] = None  # {"chapters": [...], "overall_tone": "...", "core_themes": [...]}

    # Phase 2 output
    written_chapters: list[WrittenChapter] = Field(default_factory=list)
    established_claims: list[str] = Field(default_factory=list)

    def add_chapter(self, chunk_id: str, manuscript: str):
        self.written_chapters.append(WrittenChapter(chunk_id=chunk_id, manuscript=manuscript))
        # NOTE: caller is responsible for incrementing current_chunk_index

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "WritingState":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
