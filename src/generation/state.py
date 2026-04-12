import json
import re
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from src.generation.models import ChapterDraft


class WritingPhase(str, Enum):
    PREPARE = "prepare"
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"


class WritingState(BaseModel):
    """断点状态"""
    book_id: str
    book_title: str
    phase: WritingPhase = WritingPhase.PREPARE
    current_chunk_index: int = 0
    drafts: list[ChapterDraft] = Field(default_factory=list)
    outline: Optional[dict] = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "WritingState":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @classmethod
    def get_state_path(cls, book_id: str, output_dir: str, book_title: str) -> Path:
        safe = re.sub(r'[<>:"/\\|?*]', '_', book_title)
        return Path(output_dir) / safe / "writing_state.json"

    def full_draft(self) -> str:
        """重建完整草稿"""
        return "\n\n---\n\n".join([d.chapter_text for d in self.drafts])
