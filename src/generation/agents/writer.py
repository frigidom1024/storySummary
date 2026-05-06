import os
from typing import Optional

from langchain.agents import create_agent

from src.core.node_generator import create_llm
from src.generation.agents.models import Draft
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
        completed_drafts: list[Draft],
        book_id: str,
        style_key: Optional[str] = None,
        custom_rules: Optional[str] = None,
        reference_script: Optional[str] = None,
        outline: Optional[list[dict]] = None,
        narrative_style: Optional[str] = None,
    ) -> str:
        chapter_title = chunk.chapter or f"第{chunk.order + 1}章"
        nodes_text = self._format_nodes(nodes)
        last_draft = completed_drafts[-1].content if completed_drafts else "（无）"
        tools = ManuscriptResearchToolkit.create_tools(book_id=book_id)

        system_prompt = build_style_system_prompt(style_key, custom_rules)

        # 添加从参考稿提取的叙述风格
        if narrative_style:
            system_prompt += f"\n\n## 原文叙述风格参考\n{narrative_style}"

        system_prompt += """
## 写作要求（严格遵守）
1. 只讲述当前章节的故事内容，像朗读小说一样直接叙述
2. 完全不做任何评析、不做任何总结、不发表任何个人观点
3. 可以参考前一章内容保持连贯性，但绝对不要做章节间的衔接
4. 绝对不要添加"好，咱们接着聊"、"咱们继续"、"这一章啊"等任何开头介绍或承接语
6. 不要在结尾做总结
7. 直接开始讲述故事，不要加标题，不要加任何引导语
8. 用口语化的语言自然流畅地叙述
"""

        user_prompt = f"""
## 前一章内容参考（仅用于了解故事背景，不要衔接）
{last_draft}

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