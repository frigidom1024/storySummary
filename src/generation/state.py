import json
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from src.generation.models import Draft


class WritingPhase(str, Enum):
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"


class PipelinePhase(str, Enum):
    OUTLINING = "outlining"       # 阶段1：生成梗概和结构
    STYLE_LEARNING = "style_learning"  # 阶段2：学习风格
    WRITING = "writing"           # 阶段3：写草稿
    POLISHING = "polishing"       # 阶段4：润色
    DONE = "done"                 # 完成


class WritingState(BaseModel):
    """最小状态：当前进度 + 已完成草稿。"""

    book_id: str
    book_title: str
    phase: PipelinePhase = PipelinePhase.WRITING
    current_chunk_index: int = 0
    drafts: list[Draft] = Field(default_factory=list)

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

    def add_draft(self, section_id: str, draft_type: str, content: str) -> None:
        self.drafts.append(Draft(section_id=section_id, draft_type=draft_type, content=content))
        self.current_chunk_index += 1

    def full_draft(self) -> str:
        sorted_drafts = sorted(self.drafts, key=lambda d: d.section_id)
        return "\n\n---\n\n".join(d.content for d in sorted_drafts)
