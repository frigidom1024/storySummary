import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.core.prompts import CHAPTER_WRITING_PROMPT
from src.core.node_generator import create_llm


class ChapterWriter:
    """单章生成器"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def write(
        self,
        chunk: Chunk,
        nodes: list[NarrativeNode],
        context_summary: str,
    ) -> str:
        """
        生成单章播客稿
        返回: chapter_text - 本章生成的稿子
        """
        nodes_summary = self._format_nodes(nodes)

        prompt = CHAPTER_WRITING_PROMPT.format(
            chapter_title=chunk.chapter or f"第{chunk.order + 1}章",
            chapter_summary=f"约{len(chunk.text)}字",
            core_themes="（待补充）",
            established_claims=context_summary or "（无）",
            nodes_summary=nodes_summary,
            chunk_text=chunk.text[:8000],
        )

        messages = [
            SystemMessage(content="你是一个播客主播，输出纯文本稿子。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")

        return response.content.strip()

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if n.characters else "无"
            lines.append(
                f"节点{i+1}: [{n.narrative_role}] {n.scene}\n"
                f"  情境: {n.situation}\n"
                f"  转折: {n.turning_point or '无'}\n"
                f"  情绪弧: {n.emotional_arc or '无'} | 氛围: {n.mood_tone or '无'}\n"
                f"  角色: {chars}"
            )
        return "\n\n".join(lines)
