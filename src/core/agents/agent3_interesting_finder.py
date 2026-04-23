"""Agent3: Interesting Points Finder - 有趣点发现"""
import json
import logging
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from src.core.agents.tools import AgentTools
from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class InterestingPointResult(BaseModel):
    node_id: str
    discussion_prompts: list[str] = Field(default_factory=list, description="Discussion anchors for podcast")


def create_interesting_llm(api_key: str | None = None) -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    kwargs = {"api_key": api_key, "model": model, "temperature": 0.7}
    if api_base:
        kwargs["openai_api_base"] = api_base
    return ChatOpenAI(**kwargs)


class Agent3InterestingFinder:
    """Agent3: 发现叙事中有趣的点，生成讨论话题

    职责：
    - 分析每个叙事节点，找出值得讨论的点
    - 生成播客形式的讨论话题
    - 识别伏笔、悬念、对比、反转等
    """

    def __init__(self, api_key: str = None, book_id: str = None):
        self.llm = create_interesting_llm(api_key=api_key) if api_key or os.getenv("DEEPSEEK_API_KEY") else None
        self.agent_tools = AgentTools(book_id=book_id)

    def set_search_fn(self, fn):
        self.agent_tools.set_search_fn(fn)

    def set_get_thread_last_fn(self, fn):
        self.agent_tools.set_get_thread_last_fn(fn)

    def get_tools(self):
        return self.agent_tools.get_tools()

    async def find(self, nodes: list[dict], context: dict | None = None) -> list[dict]:
        """为每个节点发现有趣点

        Args:
            nodes: 叙事节点列表
            context: 上下文信息，包含 chunk_text 等
        """
        if not nodes:
            return []

        debug_log("agent3", "Agent3InterestingFinder.find called with {} nodes, context_keys={}",
                  len(nodes), list(context.keys()) if context else [])

        if self.llm is None:
            debug_log("agent3", "No LLM configured, returning empty discussion_prompts")
            return self._build_with_defaults(nodes)

        # 构建 prompt，包含上下文
        prompt = self._build_prompt(nodes, context)
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a creative content analyst. Output ONLY JSON array."),
            HumanMessage(content=prompt)
        ])

        content = response.content if getattr(response, "content", None) else "[]"
        debug_log("agent3", "LLM response length={} preview={}", len(content), content[:200])

        # 解析结果
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)

        try:
            llm_results = json.loads(content) if isinstance(json.loads(content), list) else []
            debug_log("agent3", "Parsed {} results", len(llm_results))
        except Exception as e:
            logger.warning("Failed to parse interesting points: %s", content[:200])
            debug_log("agent3", "Parse failed: {}, using defaults", str(e))
            return self._build_with_defaults(nodes)

        # 合并结果
        return self._merge_results(nodes, llm_results)

    def _build_prompt(self, nodes: list[dict], context: dict | None = None) -> str:
        """构建提示词

        Args:
            nodes: 叙事节点列表
            context: 上下文信息，包含 chunk_text 等
        """
        nodes_summary = []
        for node in nodes:
            nodes_summary.append({
                "id": node.get("id", ""),
                "scene": node.get("scene", ""),
                "situation": node.get("situation", ""),
                "turning_point": node.get("turning_point", ""),
                "characters": [c.get("name", "") for c in node.get("characters", [])],
            })

        # 原始文本上下文
        chunk_context = ""
        if context and context.get("chunk_text"):
            chunk_context = f"\n\n原始文本片段：\n{context['chunk_text'][:2000]}"  # 限制长度

        return f"""分析以下叙事节点，为每个节点生成讨论话题（用于播客讨论）。{chunk_context}

叙事节点：
{json.dumps(nodes_summary, ensure_ascii=False, indent=2)}

请为每个节点生成 1-3 个讨论话题。讨论话题应该：
1. 触及读者情感共鸣点
2. 引发思考或辩论
3. 揭示角色动机或故事深层含义

输出格式为 JSON 数组：
[
  {{"node_id": "节点ID", "discussion_prompts": ["话题1", "话题2"]}},
  ...
]

请用中文生成话题。
"""

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
