from src.models.narrative_node import NarrativeNode
from src.generation.models import ChapterDraft


class WritingContext:
    """对话上下文，维护草稿摘要和 AI 记忆"""

    def __init__(self):
        self.drafts: list[ChapterDraft] = []
        self.context_summary: str = ""  # 压缩后的上下文摘要
        self.chapter_summaries: list[str] = []  # 每章的一句话摘要

    def build_prompt_context(self, chunk, nodes: list[NarrativeNode]) -> str:
        """生成 AI 提示词上下文

        只传递压缩摘要，不传完整历史内容，避免上下文过长
        """
        parts = []

        # 传递已建立的上下文摘要（压缩后的情节进展）
        if self.context_summary:
            parts.append(f"【前情概要】\n{self.context_summary}\n")

        # 节点作为快速索引参考，不是主要内容来源
        if nodes:
            nodes_text = self._format_nodes_brief(nodes)
            parts.append(f"【本章结构索引】\n{nodes_text}\n")

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
        """更新上下文摘要 - 压缩为情节进展摘要"""
        if not self.drafts:
            self.context_summary = ""
            self.chapter_summaries = []
            return

        # 生成每章的一句话摘要
        self.chapter_summaries = []
        for draft in self.drafts:
            # 提取章节开头100字作为摘要基础
            first_100 = draft.chapter_text[:200].replace('\n', ' ')
            self.chapter_summaries.append(first_100)

        # 压缩上下文：只保留最近2章的摘要 + 整体情节线索
        recent = self.chapter_summaries[-2:] if len(self.chapter_summaries) > 1 else self.chapter_summaries
        self.context_summary = f"（已写 {len(self.drafts)} 章）\n" + "\n".join([
            f"第{i+1}章: {s}..."
            for i, s in enumerate(recent)
        ])

    def _format_nodes_brief(self, nodes: list[NarrativeNode]) -> str:
        """简洁的节点格式 - 仅用于快速索引"""
        lines = []
        for i, n in enumerate(nodes):
            lines.append(f"节点{i+1}: {n.scene}")
        return "\n".join(lines)

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        """完整的节点格式 - 保留但减少使用"""
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if n.characters else "无"
            lines.append(
                f"节点{i+1}: {n.scene}\n"
                f"  情境: {n.situation}\n"
                f"  角色: {chars}"
            )
        return "\n".join(lines)
