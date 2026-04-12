from pydantic import BaseModel


class ChapterDraft(BaseModel):
    """单章草稿"""
    chunk_id: str 
    chapter_text: str


class ManuscriptResult(BaseModel):
    """生成结果"""
    title: str
    drafts: list[ChapterDraft]
    phase: str
    chapters_written: int
    total_chunks: int

    @property
    def full_manuscript(self) -> str:
        """重建完整稿子"""
        return "\n\n---\n\n".join([d.chapter_text for d in self.drafts])
