import json
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from src.generation.models import ChapterDraft


class WritingPhase(str, Enum):
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"


class WritingState(BaseModel):
    """最小状态：当前进度 + 已完成草稿。"""

    book_id: str
    book_title: str
    phase: WritingPhase = WritingPhase.WRITING
    current_chunk_index: int = 0
    drafts: list[ChapterDraft] = Field(default_factory=list)

    @classmethod
    def get_state_path(cls, book_id: str, output_dir: str, book_title: str) -> Path:
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", book_title)
        return Path(output_dir) / safe_title / "writing_state.json"

    @classmethod
    def load(cls, path: Path) -> "WritingState":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def add_draft(self, chunk_id: str, chapter_text: str) -> None:
        self.drafts.append(ChapterDraft(chunk_id=chunk_id, chapter_text=chapter_text))
        self.current_chunk_index += 1

    def full_draft(self) -> str:
        return "\n\n---\n\n".join(d.chapter_text for d in self.drafts)
