import os
from typing import Optional

from langchain.agents import create_agent

from src.core.node_generator import create_llm
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
        book_id: str,
        style_key: Optional[str] = None,
        custom_rules: Optional[str] = None,
        reference_script: Optional[str] = None,
        outline: Optional[list[dict]] = None,
        narrative_style: Optional[str] = None,
    ) -> str:
        chapter_title = chunk.chapter or f"第{chunk.order + 1}章"
        nodes_text = self._format_nodes(nodes)
        last_draft = completed_drafts[-1].chapter_text if completed_drafts else "（无）"
        tools = ManuscriptResearchToolkit.create_tools(book_id=book_id)

        system_prompt = build_style_system_prompt(style_key, custom_rules)

        # 添加从参考稿提取的叙述风格
        if narrative_style:
            system_prompt += f"\n\n## 原文叙述风格参考\n{narrative_style}"

        system_prompt += """

## 增量写作规则
- 你每次只写当前章节，但必须保持全书叙事一致。
- 已完成草稿代表既有口吻和视角，优先保持一致。
- 本章事实以"本章完整原文"为准，不捏造剧情。
- 直接输出本章口播稿，不加标题，不加解释。"""

        user_prompt = f"""
## 故事结构定位
当前章节在全书的整体结构中的位置：
"""
        if outline:
            # 找到当前章节在 outline 中的位置
            current_idx = None
            for i, section in enumerate(outline):
                if section.get("type") == "story_content" and section.get("chapter") == chunk.order + 1:
                    current_idx = i
                    break

            if current_idx is not None:
                # 显示前后各2个章节的结构
                start = max(0, current_idx - 2)
                end = min(len(outline), current_idx + 3)
                nearby = outline[start:end]

                outline_text = "\n".join(
                    f"- {'[当前]' if i == current_idx else ''}{s.get('section', '未知')}：{s.get('description', '')[:50]}..."
                    for i, s in enumerate(nearby, start=start)
                )
                user_prompt += f"\n{nearby[0].get('section', '未知')}前后结构：\n{outline_text}\n"
        else:
            user_prompt += "（无大纲信息）"

        user_prompt += f"""
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
以下全文仅供参考，你只需要专心写好当前章节即可，不要受全文结构影响：
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