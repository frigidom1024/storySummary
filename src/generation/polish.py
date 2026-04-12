import os
from typing import TYPE_CHECKING
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.node_generator import create_llm

if TYPE_CHECKING:
    from src.models.chunk import Chunk
    from src.generation.models import ChapterDraft


POLISH_SYSTEM_PROMPT = """你是一个播客稿编辑。你的任务是对多章节播客稿进行全局润色。

## 润色要求

1. **消除重复**：各章节间可能重复的观点、表述要合并/删除
2. **统一语气**：确保口语化风格一致，没有书面语残留
3. **强化过渡**：检查章与章之间的过渡句是否自然
4. **升华结尾**：最后一章的结尾要有力量感，适当呼应全书主题
5. **个人思考**：确保每个章节都有个人思考，不是纯情节复述
6. **事实核实**：对照原文确保情节描述准确，人物对话不要凭空捏造

## 输出

直接输出润色后的完整稿子，不要说明改了哪里。
"""


class PolishPass:
    """润色器 - 带原文上下文"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def polish(
        self,
        drafts: list["ChapterDraft"],
        chunks: dict[str, "Chunk"],
    ) -> str:
        """
        润色完整草稿

        Args:
            drafts: 章节草稿列表
            chunks: chunk_id -> Chunk 映射
        """
        # 构建章节摘要
        chapters_text = self._build_chapters_text(drafts)
        chunks_context = self._build_chunks_context(chunks)

        prompt = f"""## 全文稿子
---
{chapters_text}
---

## 原文参考（用于核实事实）
---
{chunks_context}
---

请对照原文核实稿子中的情节描述，如有错误请修正。输出润色后的完整稿子。"""

        messages = [
            SystemMessage(content=POLISH_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")

        return response.content.strip()

    def _build_chapters_text(self, drafts: list["ChapterDraft"]) -> str:
        """构建章节文本"""
        parts = []
        for i, draft in enumerate(drafts, 1):
            parts.append(f"【第{i}章】\n{draft.chapter_text}")
        return "\n\n---\n\n".join(parts)

    def _build_chunks_context(self, chunks: dict[str, "Chunk"]) -> str:
        """构建原文上下文"""
        parts = []
        for chunk_id, chunk in chunks.items():
            title = chunk.chapter or f"章节{chunk.order + 1}"
            # 截取前 2000 字作为参考
            text_preview = chunk.text[:2000] + "..." if len(chunk.text) > 2000 else chunk.text
            parts.append(f"【{title}】\n{text_preview}")
        return "\n\n---\n\n".join(parts)
