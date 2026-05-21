import os
import random
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
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.5)

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

        # 从 outline 中获取主人公名字、原文叙述视角和目标长度
        protagonist = "主角"  # 默认值
        original_person = "first"  # 默认假设原文是第一人称
        target_length = 600  # 默认目标长度
        if outline and isinstance(outline, list):
            for section in outline:
                if section.get("type") == "story_content" and section.get("chapter") == chunk.order:
                    protagonist = section.get("protagonist", "主角")
                    original_person = section.get("narrative_person", "first")
                    target_length = section.get("target_length", 600)
                    break

        system_prompt = build_style_system_prompt(style_key, custom_rules)

        # 添加从参考稿提取的叙述风格
        if narrative_style:
            system_prompt += f"\n\n## 参考口播稿的风格特点\n{narrative_style}"

        # 添加完整口播稿参考中的故事叙述风格
        if reference_script:
            system_prompt += f"""

## 完整口播稿参考（学习其故事叙述风格）
请学习以下口播稿的故事叙述方式，包括叙述节奏、用词、句式等：
```
{reference_script[:3000]}...
```
"""

        system_prompt += """
## 写作要求（严格遵守，违反任何一条将导致任务失败）
1. 【强制】必须使用第三人称视角（他/她/他们）讲述故事，绝对禁止使用第一人称（我/我们）
2. 【强制】将原文中的"我"全部替换为主人公名字或"他"
3. 只讲述当前章节的故事内容，像朗读小说一样直接叙述
4. 完全不做任何评析、不做任何总结、不发表任何个人观点
5. 可以参考前一章内容保持连贯性，但绝对不要做章节间的衔接
6. 绝对不要添加"好，咱们接着聊"、"咱们继续"、"这一章啊"等任何开头介绍或承接语
7. 不要在结尾做总结
8. 直接开始讲述故事，不要加标题，不要加任何引导语
9. 用口语化的语言自然流畅地叙述
10. 叙述视角必须保持一致，全程使用第三人称，不要切换视角
"""

        # 根据原文叙述视角决定是否需要转换
        conversion_note = f"原文是第一人称叙事，请将'我'转换为'{protagonist}'（即第三人称'他'）" if original_person == "first" else "原文是第三人称叙事，请保持第三人称视角"

        # 随机选取 chunk 中的讨论问题作为思考方向参考（0-2个）
        discussion_prompts_text = ""
        selected_prompts = []
        if hasattr(chunk, 'discussion_prompts') and chunk.discussion_prompts:
            prompts = chunk.discussion_prompts
            # 随机选择0-2个问题（可以不选）
            num_prompts = min(random.randint(0, 2), len(prompts))
            if num_prompts > 0:
                selected_prompts = random.sample(prompts, num_prompts)
                discussion_prompts_text = "\n".join(f"- {p}" for p in selected_prompts)
            # 直接打印选中的讨论点
            if selected_prompts:
                print(f"\n[WRITER DEBUG] Selected discussion prompts for chapter '{chapter_title}':")
                for i, prompt in enumerate(selected_prompts, 1):
                    print(f"  {i}. {prompt}")
            else:
                print(f"\n[WRITER DEBUG] No discussion prompts selected for chapter '{chapter_title}'")
        
        user_prompt = f"""
## 故事基本信息
- 主人公名字: {protagonist}
- 原文叙述视角: {original_person}

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

## 思考方向（请在叙述中穿插你的主观分析和见解，用括号括起来作为旁白或点评，例如：[这种被动接受的态度，正是存在主义中"荒诞"的体现]，让观众能够清晰地听到你的思考）
{discussion_prompts_text}

## 叙述视角转换要求
{conversion_note}。请使用第三人称（他/她/他们）讲述故事，不要使用第一人称（我/我们）。

## 输出格式要求
请直接输出转换后的第三人称故事叙述，不要包含任何格式标记、标题、注释或其他内容。输出必须是纯文本故事叙述。
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