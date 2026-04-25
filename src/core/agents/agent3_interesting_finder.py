"""Agent3: Interesting Points Finder - 有趣点发现"""
import json
import logging
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class InterestingPointResult(BaseModel):
    node_id: str
    discussion_prompts: list[str] = Field(default_factory=list, description="Discussion anchors for podcast")


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return ChatOpenAI(**llm_kwargs)


def create_interesting_tools(book_id: str):
    """Create tools for interesting points finder agent with auto-bound book_id."""

    @tool
    def output_discussion_prompts(prompts: str) -> str:
        """Output the final discussion prompts JSON. Use this when you have completed the analysis."""
        return prompts

    return [output_discussion_prompts]


class Agent3InterestingFinder:
    """Agent3: 使用LangChain Agent发现叙事中的有趣点，生成讨论话题"""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id
        
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        
        if api_key:
            self.llm = create_llm(api_key=api_key, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

    def _create_agent(self):
        """Create a LangChain agent for interesting points finding."""
        tools = create_interesting_tools(self.book_id) if self.book_id else []
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a creative content analyst. Your task is to find interesting points in narrative nodes and generate discussion prompts for podcast.

For each node, generate 1-3 discussion prompts that:
1. Touch readers' emotional resonance points
2. Provoke thinking or debate
3. Reveal character motivations or deeper story meanings

Discussion prompts should be in Chinese and be engaging."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessage(content="""Analyze these narrative nodes and generate discussion prompts:

Nodes:
{nodes}

{context}

Output format: JSON array with node_id and discussion_prompts array:
[
  {{"node_id": "节点ID", "discussion_prompts": ["话题1", "话题2"]}},
  ...
]

Output your final answer using the output_discussion_prompts tool."""),
        ])

        agent = create_react_agent(self.llm, tools, prompt=prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=5)

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
            
            result = await agent_executor.ainvoke({
                "nodes": json.dumps(nodes, ensure_ascii=False),
                "context": context_str
            })

            output = result.get("output", "")
            debug_log("agent3", "Agent output: {}", output[:500])

            llm_results = self._parse_results(output)
            
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
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

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
