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
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.7, max_tokens=4000)

    async def write_intro(
        self,
        book_id: str,
        chunk: Chunk = None,
        style_key: Optional[str] = None,
        intro_style: Optional[str] = None,
        book_title: str = None,
    ) -> str:
        """生成开篇介绍

        Args:
            book_id: 书籍ID
            chunk: 包含书籍信息的 chunk（可选）
            style_key: 风格配置
            intro_style: 开篇介绍风格
            book_title: 书籍标题（当 chunk 不可用时使用）

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
- 直接输出介绍内容，不加标题，不加解释
- 禁止添加任何收尾性语句（如"下期再见"等）
- 以第三人称叙述，不代入故事角色"""

        title = book_title or (chunk.chapter if chunk else None) or "未知"
        content_preview = chunk.text[:500] + "..." if chunk and chunk.text else ""

        user_prompt = f"""请生成一段口播稿开篇介绍。

书籍信息：
- 书名: {title}
- 内容预览: {content_preview if content_preview else "无预览内容"}

请使用搜索工具查询作者信息和书籍背景。

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
        chunk: Chunk = None,
        completed_drafts: list[str] = None,
        style_key: Optional[str] = None,
        reflection_style: Optional[str] = None,
        book_title: str = None,
    ) -> str:
        """生成总结思考

        Args:
            book_id: 书籍ID
            chunk: 包含书籍信息的 chunk（可选）
            completed_drafts: 已完成的口播稿章节列表
            style_key: 风格配置
            reflection_style: 总结思考风格
            book_title: 书籍标题（当 chunk 不可用时使用）

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
- 直接输出内容，不加标题，不加解释
- 禁止添加任何收尾性语句（如"下期再见"等）
- 以第三人称叙述，不代入故事角色"""

        title = book_title or (chunk.chapter if chunk else None) or "未知"

        user_prompt = f"""请基于全书口播稿内容，生成一段总结和思考。

书籍信息：
- 书名: {title}

全书口播稿内容：
{full_manuscript if full_manuscript else "（暂无正文内容）"}

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
        def search_author_info(query: str) -> str:
            """搜索作者和书籍相关信息

            Args:
                query: 搜索查询词
            """
            try:
                from duckduckgo_search import DDGS
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=3):
                        title = r.get("title", "")
                        body = r.get("body", "")
                        if title and body:
                            results.append(f"{title}\n{body}")
                if results:
                    return "\n\n".join(results)
                return f"未找到关于 '{query}' 的搜索结果"
            except Exception as e:
                return f"搜索失败: {str(e)}"

        return [search_author_info]

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