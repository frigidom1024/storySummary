"""Guide Agent - 生成开篇介绍和总结思考"""
import json
import os
from typing import Optional

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
from src.logging_config import debug
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.prompts import build_style_system_prompt


class GuideAgent:
    """生成开篇介绍和总结思考的 Agent"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.7)

    async def write_intro(
        self,
        book_id: str,
        chunk: Chunk,
        style_key: Optional[str] = None,
        intro_style: Optional[str] = None,
    ) -> str:
        """生成开篇介绍

        Args:
            book_id: 书籍ID
            chunk: 包含书籍信息的 chunk（如有）
            style_key: 风格配置
            intro_style: 开篇介绍风格

        Returns:
            生成的开篇介绍文本
        """
        tools = self._create_search_tools()

        system_prompt = build_style_system_prompt(style_key)

        if intro_style:
            system_prompt += f"\n\n## 开篇风格参考\n{intro_style}"

        system_prompt += """

## 开篇介绍规则
- 生成一段吸引人的开篇介绍，用于口播稿开头
- 介绍作者和书籍背景，引发听众兴趣
- 语气亲切、口语化，像朋友聊天
- 长度适中（300-500字）
- 直接输出介绍内容，不加标题，不加解释"""

        user_prompt = f"""请生成一段口播稿开篇介绍。

书籍信息：
- 书名: {chunk.chapter or "未知"}
- 内容: {chunk.text[:500]}{"..." if len(chunk.text) > 500 else ""}

你可以使用搜索工具查询作者信息和书籍背景。

直接输出开篇介绍内容，不要包含任何其他内容。"""

        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
            debug=self.debug_mode,
            name="guide-intro-agent",
        )

        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_prompt}]
        })

        return self._extract_output(response)

    async def write_reflection(
        self,
        book_id: str,
        chunk: Chunk,
        completed_drafts: list[str],
        style_key: Optional[str] = None,
        reflection_style: Optional[str] = None,
    ) -> str:
        """生成总结思考

        Args:
            book_id: 书籍ID
            chunk: 包含书籍信息的 chunk（如有）
            completed_drafts: 已完成的口播稿章节列表
            style_key: 风格配置
            reflection_style: 总结思考风格

        Returns:
            生成的总结思考文本
        """
        full_manuscript = "\n\n".join(completed_drafts) if completed_drafts else ""

        system_prompt = build_style_system_prompt(style_key)

        if reflection_style:
            system_prompt += f"\n\n## 总结风格参考\n{reflection_style}"

        system_prompt += """

## 总结思考规则
- 基于全书口播稿内容，生成一段总结和思考
- 总结故事主题、人物命运、核心感悟
- 引发听众进一步思考
- 语气亲切、口语化，像朋友聊天
- 长度适中（300-500字）
- 直接输出内容，不加标题，不加解释"""

        user_prompt = f"""请基于全书口播稿内容，生成一段总结和思考。

书籍信息：
- 书名: {chunk.chapter or "未知"}

全书口播稿内容：
{full_manuscript}

直接输出总结思考内容，不要包含任何其他内容。"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            return self._extract_output(response)
        except Exception as e:
            debug("guide", "[REFLECTION] failed: {}", str(e))
            return ""

    def _create_search_tools(self):
        """创建搜索工具"""
        from langchain_core.tools import tool

        @tool
        def search_author_info(author_name: str) -> str:
            """搜索作者相关信息

            Args:
                author_name: 作者姓名
            """
            # 实际实现需要接入搜索服务
            # 这里返回模拟数据占位
            return f"作者信息搜索: {author_name}。建议搜索作者生平、创作风格、重要作品等。"

        @tool
        def search_book_background(book_title: str) -> str:
            """搜索书籍背景信息

            Args:
                book_title: 书名
            """
            # 实际实现需要接入搜索服务
            return f"书籍背景搜索: {book_title}。建议搜索创作背景、文学评价、社会影响等。"

        return [search_author_info, search_book_background]

    def _extract_output(self, response) -> str:
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                return "".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content
                ).strip()
            return str(content).strip()
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
