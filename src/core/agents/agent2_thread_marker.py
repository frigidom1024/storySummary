"""Agent2: Thread Marker - 叙事线标记"""
import json
import logging
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from src.prompts.graph_builder_prompt import GRAPH_BUILDER_PROMPT
from src.core.agents.tools import AgentTools

from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class ThreadMarkResult(BaseModel):
    node_id: str
    thread_hint: str = Field(default="main", description="main/new/uncertain")
    link_confidence: float = 0.5


class ThreadState:
    """维护叙事线状态"""

    def __init__(self):
        self.threads: dict[str, set[str]] = {}
        self.last_node_in_thread: dict[str, str] = {}

    def add_thread(self, thread_id: str, characters: list[str]) -> None:
        if thread_id not in self.threads:
            self.threads[thread_id] = set()
        self.threads[thread_id].update(characters)

    def set_last_node(self, thread_id: str, node_id: str) -> None:
        self.last_node_in_thread[thread_id] = node_id

    def get_last_node(self, thread_id: str) -> str:
        return self.last_node_in_thread.get(thread_id, "")

    def find_best_thread(self, characters: list[str]) -> tuple[str | None, float]:
        if not characters:
            return None, 0.0
        src = set(characters)
        best_thread = None
        best_ratio = 0.0
        for thread_id, thread_chars in self.threads.items():
            overlap = len(src & thread_chars)
            ratio = overlap / len(src) if src else 0.0
            if ratio > best_ratio:
                best_thread = thread_id
                best_ratio = ratio
        return best_thread, best_ratio


def create_thread_marker_llm(api_key: str | None = None) -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    kwargs = {"api_key": api_key, "model": model, "temperature": 0.3}
    if api_base:
        kwargs["openai_api_base"] = api_base
    return ChatOpenAI(**kwargs)


class Agent2ThreadMarker:
    """Agent2: 叙事线标记

    职责：
    - 为每个节点分配 thread_id（main/支线等）
    - 确定 thread_prev_node_id（前置节点）
    - 确定 thread_next_node_id（后续节点）
    - 维护 thread_state 状态
    """

    def __init__(self, api_key: str = None, book_id: str = None):
        self.llm = create_thread_marker_llm(api_key=api_key) if api_key or os.getenv("DEEPSEEK_API_KEY") else None
        self.thread_state = ThreadState()
        self.agent_tools = AgentTools(book_id=book_id)

    def set_search_fn(self, fn):
        self.agent_tools.set_search_fn(fn)

    def set_get_thread_last_fn(self, fn):
        self.agent_tools.set_get_thread_last_fn(fn)

    def get_tools(self):
        return self.agent_tools.get_tools()

    def get_context_summary(self) -> dict:
        recent_nodes = []
        for thread_id, last_node in list(self.thread_state.last_node_in_thread.items())[-5:]:
            recent_nodes.append({
                "id": last_node,
                "characters": list(self.thread_state.threads.get(thread_id, set())),
                "thread_id": thread_id,
            })
        return {
            "recent_nodes": recent_nodes,
            "thread_summaries": {k: list(v) for k, v in self.thread_state.threads.items()},
        }

    async def mark(self, nodes: list[dict], context: dict | None = None) -> list[dict]:
        """标记节点的叙事线信息

        Args:
            nodes: 叙事节点列表
            context: 上下文信息，包含 chunk_text 等
        """
        if not nodes:
            return []
        debug_log("agent2", "Agent2ThreadMarker.mark called with {} nodes, context_keys={}",
                  len(nodes), list(context.keys()) if context else [])

        if self.llm is None:
            debug_log("agent2", "LLM disabled, using defaults")
            return self._build_with_defaults(nodes)

        context = self.get_context_summary()
        debug_log("agent2", "Context: threads={} recent={}", list(context["thread_summaries"].keys()), len(context["recent_nodes"]))

        prompt = GRAPH_BUILDER_PROMPT.format(
            nodes=json.dumps(nodes, ensure_ascii=False),
            recent_nodes=json.dumps(context["recent_nodes"], ensure_ascii=False),
            thread_summaries=json.dumps(context["thread_summaries"], ensure_ascii=False),
        )
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a narrative structure analyst. Output ONLY JSON array."),
            HumanMessage(content=prompt),
        ])
        content = response.content if getattr(response, "content", None) else "[]"
        debug_log("agent2", "LLM response length={}", len(content))

        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)

        try:
            llm_results = json.loads(content)
            debug_log("agent2", "Parsed {} results", len(llm_results))
        except Exception as e:
            logger.warning("Failed to parse thread results: %s", content[:200])
            debug_log("agent2", "Parse failed, using defaults")
            return self._build_with_defaults(nodes)

        return self._merge_results(nodes, llm_results)

    def _merge_results(self, nodes: list[dict], llm_results: list[dict]) -> list[dict]:
        """合并 LLM 结果，更新 thread 信息"""
        debug_log("agent2", "_merge_results: {} nodes, {} llm_results", len(nodes), len(llm_results))
        result_map = {r.get("node_id", ""): r for r in llm_results}

        for idx, node in enumerate(nodes):
            node_id = node.get("id", "")
            characters = [c.get("name", "") for c in node.get("characters", []) if c.get("name")]
            llm_hint = result_map.get(node_id, {})

            # 分配 thread_id
            thread_id, _ = self._assign_thread(llm_hint, characters)
            node["thread_id"] = thread_id

            # 设置前置节点
            node["thread_prev_node_id"] = self.thread_state.get_last_node(thread_id)

            debug_log("agent2", "  node[{}] id={} thread={} prev={}",
                      idx, node_id, thread_id, node["thread_prev_node_id"])

            # 更新 thread state
            self.thread_state.add_thread(thread_id, characters)
            self.thread_state.set_last_node(thread_id, node_id)

        debug_log("agent2", "Final threads: {}", list(self.thread_state.threads.keys()))
        return nodes

    def _assign_thread(self, llm_hint: dict, characters: list[str]) -> tuple[str, str]:
        """根据 LLM 提示和角色分配 thread"""
        hint = llm_hint.get("thread_hint", "main")

        if hint == "new" or not self.thread_state.threads:
            thread_id = "main" if not self.thread_state.threads else f"thread_{len(self.thread_state.threads)}"
            return thread_id, hint

        best_thread, ratio = self.thread_state.find_best_thread(characters)
        if best_thread and ratio >= 0.5:
            return best_thread, "main"
        return f"thread_{len(self.thread_state.threads)}", hint

    def _build_with_defaults(self, nodes: list[dict]) -> list[dict]:
        """使用默认值构建"""
        for node in nodes:
            node.setdefault("thread_id", "main")
            node.setdefault("thread_name", "")
            node.setdefault("thread_prev_node_id", "")
            node.setdefault("thread_next_node_id", "")
        return nodes
