import os
from typing import Optional

from langchain.agents import create_agent

from src.core.node_generator import create_llm
from src.generation.context import StoryContext
from src.generation.models import ChapterDraft
from src.generation.research_tools import ManuscriptResearchToolkit
from src.logging_config import debug
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.prompts import build_style_system_prompt


class ChapterWriter:
    """逐章写作 agent。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.7)

    async def write(
        self,
        chunk: Chunk,
        nodes: list[NarrativeNode],
        completed_drafts: list[ChapterDraft],
        global_outline: str,
        book_id: str,
        all_chunks: list[Chunk],
        all_nodes: list[NarrativeNode],
        style_profile: Optional[str] = None,
        style_key: Optional[str] = None,
        custom_rules: Optional[str] = None,
        reference_script: Optional[str] = None,
    ) -> str:
        chapter_title = chunk.chapter or f"第{chunk.order + 1}章"
        nodes_text = self._format_nodes(nodes)
        memory_text = StoryContext.build_memory(completed_drafts)
        last_draft = completed_drafts[-1].chapter_text[-1200:] if completed_drafts else "（无）"
        tools = ManuscriptResearchToolkit.create_tools(book_id=book_id, chunks=all_chunks, nodes=all_nodes)

        system_prompt = build_style_system_prompt(style_key, custom_rules) + """

## 增量写作规则
- 你每次只写当前章节，但必须保持全书叙事一致。
- 已完成草稿代表既有口吻和视角，优先保持一致。
- 必须先利用“全书故事大纲”确认伏笔、锚点和关系变化所在位置。
- 本章事实以“本章完整原文”为准，不捏造剧情。
- 写作前至少调用一次原文查找工具，必要时调用向量检索工具核验伏笔/回收点。
- 直接输出本章口播稿，不加标题，不加解释。"""

        user_prompt = f"""
## 已完成草稿记忆
{memory_text}

## 紧邻前文章节尾部（用于衔接语气）
```上章
{last_draft}
```

## 当前章节
- 标题: {chapter_title}
- 原文长度: {len(chunk.text)} 字

## 当前章节节点索引
{nodes_text}

## 当前章节完整原文
```原文
{chunk.text}
```
"""

        if reference_script:
            user_prompt += f"""
## 参考口播稿（仅学习风格）
```参考
{reference_script}
```
"""

        if self.debug_mode:
            debug("writer", "[WRITE] chapter={} drafts={}", chapter_title, len(completed_drafts))
            debug("writer", "[WRITE] prompt_length={}", len(user_prompt))

        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
            debug=self.debug_mode,
            name="chapter-writer-agent",
        )
        response = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ]
            }
        )
        output = self._extract_output(response)
        if not output:
            raise ValueError("LLM returned empty response")
        return output

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        if not nodes:
            return "（无节点）"
        return "\n".join(f"节点{i + 1}: {n.scene}" for i, n in enumerate(nodes))

    def _extract_output(self, response: dict) -> str:
        messages = response.get("messages", []) if isinstance(response, dict) else []
        if not messages:
            return ""
        last = messages[-1]
        content = getattr(last, "content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            ).strip()
        return str(content).strip()
