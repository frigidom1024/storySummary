"""Agent3: Interesting Points Finder - 有趣点发现"""
import json
import logging
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

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
    """Agent3: 使用LangChain Agent发现叙事中的有趣点，生成讨论话题"""

    SYSTEM_PROMPT = """You are a creative content analyst. Your task is to find interesting points in narrative nodes and generate discussion prompts for podcast.

For each node, generate 1-3 discussion prompts that:
1. Touch readers' emotional resonance points
2. Provoke thinking or debate
3. Reveal character motivations or deeper story meanings

Discussion prompts should be in Chinese and be engaging.

IMPORTANT: Output ONLY the JSON array in your response, no explanation."""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id

        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            self.llm = create_llm(api_key=api_key, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

        self.tools = []

    def _create_agent(self):
        """Create a LangChain agent for interesting points finding."""
        from langchain.agents import create_agent

        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT
        )

    async def find(self, nodes: list[dict], context: dict | None = None) -> list[dict]:
        """为每个节点发现有趣点"""
        if not nodes:
            return []

        debug_log("agent3", "Agent3InterestingFinder.find called with {} nodes", len(nodes))

        if self.llm is None:
            debug_log("agent3", "No LLM configured, returning empty discussion_prompts")
            return self._build_with_defaults(nodes)

        # 构建上下文
        context_str = ""
        if context and context.get("chunk_text"):
            context_str = f"\n\n原始文本片段：\n{context['chunk_text'][:2000]}"

        try:
            agent_executor = self._create_agent()

            user_message = f"""Analyze these narrative nodes and generate discussion prompts:

Nodes:
{json.dumps(nodes, ensure_ascii=False)}

{context_str}

Remember: Output ONLY the JSON array in your response, no explanation."""

            result = await agent_executor.ainvoke({
                "input": user_message
            })

            # LangChain 1.0 agent result structure
            if hasattr(result, 'content'):
                output = result.content if result.content else ""
            elif hasattr(result, 'messages') and result.messages:
                output = result.messages[-1].content if result.messages[-1].content else ""
            elif isinstance(result, dict):
                output = result.get("output", result.get("messages", [{}])[-1].get("content", "") if isinstance(result.get("messages"), list) else "")
            else:
                output = str(result)

            debug_log("agent3", "Agent output: {}", str(output)[:500])

            llm_results = self._parse_results(output)

            if not llm_results and output:
                logger.warning(f"Failed to parse discussion prompts from output: {output[:200]}")

        except Exception as e:
            debug_log("agent3", "Agent execution failed: {}", str(e))
            llm_results = []

        return self._merge_results(nodes, llm_results)

    def _parse_results(self, content: str) -> list:
        """Parse discussion prompts from agent output."""
        import re

        if not content:
            return []

        try:
            # Strip markdown code blocks if present
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in content
        json_match = re.search(r'\[\s*\{[^}\]]*"node_id"\s*:[^}\]]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse discussion prompts from output: {content[:200]}")
        return []

    def _merge_results(self, nodes: list[dict], llm_results: list[dict]) -> list[dict]:
        """合并 LLM 结果到节点"""
        result_map = {r.get("node_id", ""): r.get("discussion_prompts", []) for r in llm_results}

        for node in nodes:
            node_id = node.get("id", "")
            node["discussion_prompts"] = result_map.get(node_id, [])
            debug_log("agent3", "  node_id={} discussion_prompts={}", node_id, len(node.get("discussion_prompts", [])))

        return nodes

    def _build_with_defaults(self, nodes: list[dict]) -> list[dict]:
        """使用默认空值"""
        for node in nodes:
            node.setdefault("discussion_prompts", [])
        return nodes