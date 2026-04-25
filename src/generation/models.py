from pydantic import BaseModel


class ChapterDraft(BaseModel):
    chunk_id: str
    chapter_text: str


class ManuscriptResult(BaseModel):
    title: str
    drafts: list[ChapterDraft]
    phase: str
    chapters_written: int
    total_chunks: int

    @property
    def full_manuscript(self) -> str:
        return "\n\n---\n\n".join(d.chapter_text for d in self.drafts)
