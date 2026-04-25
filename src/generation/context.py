from src.generation.models import ChapterDraft


class StoryContext:
    """草稿上下文压缩器。"""

    @staticmethod
    def build_memory(drafts: list[ChapterDraft], max_items: int = 8) -> str:
        if not drafts:
            return "（暂无已写草稿）"

        lines = []
        for idx, draft in enumerate(drafts, start=1):
            preview = draft.chapter_text[:240].replace("\n", " ")
            lines.append(f"第{idx}章要点: {preview}...")

        if len(lines) <= max_items:
            return "\n".join(lines)

        head = lines[:2]
        tail = lines[-(max_items - 3):]
        return "\n".join(head + ["...（中间章节省略）..."] + tail)
