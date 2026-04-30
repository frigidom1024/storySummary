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
    intro: str = ""
    reflection: str = ""

    @property
    def full_manuscript(self) -> str:
        parts = []
        if self.intro:
            parts.append(self.intro)
        parts.extend(d.chapter_text for d in self.drafts)
        if self.reflection:
            parts.append(self.reflection)
        return "\n\n---\n\n".join(parts)
