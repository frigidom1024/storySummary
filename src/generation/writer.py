import os
from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.prompts import build_writing_prompt
from src.core.node_generator import create_llm
from src.logging_config import debug


class ChapterWriter:
    """单章生成器"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def write(
        self,
        chunk: Chunk,
        nodes: list[NarrativeNode],
        context_summary: str,
        style_key: Optional[str] = None,
        custom_rules: Optional[str] = None,
        reference_script: Optional[str] = None,
    ) -> str:
        """
        生成单章播客稿

        节点仅用于快速把握结构，实际内容基于原文 chunk.text
        """
        # 节点只传简要索引，不传完整详情
        nodes_index = self._format_nodes_brief(nodes)

        prompt_data = build_writing_prompt(
            chapter_title=chunk.chapter or f"第{chunk.order + 1}章",
            chapter_summary=f"约{len(chunk.text)}字",
            core_themes="（由AI根据全文理解后补充）",
            established_claims=context_summary or "（无）",
            nodes_summary=nodes_index,
            chunk_text=chunk.text,  # 实际写作素材
            style_key=style_key,
            custom_rules=custom_rules,
            reference_script=reference_script,
        )

        if self.debug_mode:
            debug("writer", "[WRITE] 生成章节: {}", chunk.chapter or f"第{chunk.order + 1}章")
            debug("writer", "[WRITE] Prompt 长度: {} 字", len(prompt_data["user"]))
            debug("writer", "[WRITE] Context Summary: {}",
                  context_summary[:100] + "..." if len(context_summary) > 100 else context_summary)

        messages = [
            SystemMessage(content=prompt_data["system"]),
            HumanMessage(content=prompt_data["user"])
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")

        result = response.content.strip()

        if self.debug_mode:
            debug("writer", "[WRITE] 生成完成: {} 字", len(result))

        return result

    def _format_nodes_brief(self, nodes: list[NarrativeNode]) -> str:
        """简洁的节点格式 - 仅用于快速索引定位"""
        lines = []
        for i, n in enumerate(nodes):
            lines.append(f"节点{i+1}: {n.scene}")
        return "\n".join(lines)

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        """完整节点格式 - 已简化不再使用"""
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if n.characters else "无"
            importance = getattr(n, 'importance', 0.5)
            lines.append(
                f"节点{i+1}: {n.scene} (重要性: {importance})\n"
                f"  情境: {n.situation}\n"
                f"  角色: {chars}"
            )
        return "\n\n".join(lines)
