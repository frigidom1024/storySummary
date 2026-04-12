from src.models.narrative_node import NarrativeNode
from src.generation.models import ChapterDraft


class WritingContext:
    """对话上下文，维护草稿摘要和 AI 记忆"""

    def __init__(self):
        self.drafts: list[ChapterDraft] = []
        self.context_summary: str = ""
        self.established_facts: list[str] = []

    def build_prompt_context(self, chunk, nodes: list[NarrativeNode]) -> str:
        """生成 AI 提示词上下文"""
        parts = []

        if self.context_summary:
            parts.append(f"【已写内容】\n{self.full_draft()}\n")

        if nodes:
            nodes_text = self._format_nodes(nodes)
            parts.append(f"【本章叙事节点】\n{nodes_text}\n")

        return "\n".join(parts)

    def add_draft(self, chunk_id: str, chapter_text: str) -> None:
        """添加新章节草稿"""
        self.drafts.append(ChapterDraft(chunk_id=chunk_id, chapter_text=chapter_text))
        self._update_summary()

    def update_last_draft(self, chapter_text: str) -> None:
        """更新最后一章草稿（AI 可能修改了刚生成的章节）"""
        if self.drafts:
            self.drafts[-1].chapter_text = chapter_text
            self._update_summary()

    def full_draft(self) -> str:
        """重建完整草稿"""
        return "\n\n---\n\n".join([d.chapter_text for d in self.drafts])

    def _update_summary(self) -> None:
        """更新上下文摘要（截取最后章节的前 500 字）"""
        if self.drafts:
            last_text = self.drafts[-1].chapter_text
            self.context_summary = last_text[:500] if last_text else ""
        else:
            self.context_summary = ""

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if n.characters else "无"
            lines.append(
                f"节点{i+1}: [{n.narrative_role}] {n.scene}\n"
                f"  情境: {n.situation}\n"
                f"  角色: {chars}"
            )
        return "\n".join(lines)
