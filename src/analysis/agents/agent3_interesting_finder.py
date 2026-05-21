"""Agent3: Interesting Points Finder - 有趣点发现"""
import json
import logging
import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.chunk import Chunk
from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return ChatOpenAI(**llm_kwargs)


class Agent3InterestingFinder:
    """Agent3: 为每个章节（Chunk）生成讨论话题"""

    DEFAULT_PROMPT = """You are a creative content analyst. Your task is to analyze a book chapter and extract engaging content for podcast listeners.

Generate discussion prompts based on the chapter content. Focus on:
1. Emotional resonance points
2. Thought-provoking themes
3. Character motivations and deeper meanings
4. Universal human experiences

Output a JSON array of strings. Example: ["prompt 1", "prompt 2"]

Output ONLY the JSON array, no other text."""

    def __init__(self, api_key: str = None, book_id: str = None, system_prompt: str = None):
        self.book_id = book_id
        self.system_prompt = system_prompt or self.DEFAULT_PROMPT

        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            self.llm = create_llm(api_key=api_key, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

    async def process_chunk(
        self,
        chunk: Chunk,
        extraction_hint: str = None,
    ) -> Chunk:
        """为单个章节生成讨论话题，返回更新后的 chunk。

        Args:
            chunk: 待处理的章节
            extraction_hint: 可选的提取提示，如"聚焦人物心理变化"、"关注场景转换"等

        Returns:
            更新了 discussion_prompts 字段的 chunk
        """
        if self.llm is None:
            debug_log("agent3", "No LLM configured, returning empty discussion_prompts for chunk {}", chunk.id)
            chunk.discussion_prompts = []
            return chunk

        debug_log("agent3", "Processing chunk {}: {}", chunk.id, chunk.chapter or "untitled")

        # 构建用户提示
        hint_section = f"\n\n提取要求：{extraction_hint}" if extraction_hint else ""

        user_msg = HumanMessage(content=f"""Analyze this chapter and extract engaging content:

章节标题: {chunk.chapter or "未知"}
章节内容:
{chunk.text}
{hint_section}

请根据章节内容生成讨论话题。按需生成数量（可以只有1个，也可以有10个），质量优先。直接输出 JSON 数组，不要包含任何其他内容。""")

        try:
            system_msg = SystemMessage(content=self.system_prompt)
            response = await self.llm.ainvoke([system_msg, user_msg])
            content = response.content if hasattr(response, "content") else str(response)
            debug_log("agent3", "LLM response: {}", content[:300])

            prompts = self._parse_prompts(content)
            chunk.discussion_prompts = prompts
            debug_log("agent3", "Generated {} discussion prompts for chunk {}", len(prompts), chunk.id)

        except Exception as e:
            debug_log("agent3", "Agent execution failed for chunk {}: {}", chunk.id, str(e))
            chunk.discussion_prompts = []

        return chunk

    def _parse_prompts(self, content: str) -> list[str]:
        """解析 LLM 返回的讨论话题列表"""
        if not content:
            return []

        import re

        # 清理 markdown 代码块
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and all(isinstance(p, str) for p in parsed):
                return parsed
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 数组
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list) and all(isinstance(p, str) for p in parsed):
                    return parsed
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse discussion prompts from: {content[:200]}")
        return []

    async def process_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """批量处理多个章节

        Args:
            chunks: 待处理的章节列表

        Returns:
            更新了 discussion_prompts 的章节列表
        """
        results = []
        for chunk in chunks:
            await self.process_chunk(chunk)
            results.append(chunk)
        return results