"""Agent2: Thread Marker - 叙事线标记"""
import json
import logging
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.storage.book_repository import BookRepository

from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class ThreadMarkResult(BaseModel):
    """Agent2输出模型 - 与NarrativeNode的thread字段一致"""
    node_id: str
    thread_id: str = Field(default="main", description="Thread ID")
    thread_name: str = Field(default="", description="Thread name")
    thread_prev_node_id: str = Field(default="", description="Previous node ID in same thread")
    thread_next_node_id: str = Field(default="", description="Next node ID in same thread")


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

    def get_context_summary(self) -> dict:
        recent_nodes = []
        for thread_id, last_node in list(self.last_node_in_thread.items())[-5:]:
            recent_nodes.append({
                "id": last_node,
                "characters": list(self.threads.get(thread_id, set())),
                "thread_id": thread_id,
            })
        return {
            "recent_nodes": recent_nodes,
            "thread_summaries": {k: list(v) for k, v in self.threads.items()},
        }


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return ChatOpenAI(**llm_kwargs)


def create_thread_tools(book_id: str):
    """Create tools for thread marker agent with auto-bound book_id."""
    from src.core.tools.tool_executor import (
        search_nodes_impl,
        get_existing_threads_impl,
    )
    @tool
    def get_existing_threads() -> str:
        """Get all existing threads. If no threads exist, return an empty list."""
        result = get_existing_threads_impl(book_id=book_id)
        return json.dumps(result if result else [], ensure_ascii=False)

    @tool
    def search_nodes(keyword: str) -> str:
        """Search nodes by character name or keyword."""

        result = search_nodes_impl(book_id=book_id, keyword=keyword)
        return json.dumps(result, ensure_ascii=False)

    @tool
    def output_thread_markers(markers: str) -> str:
        """Output the final thread markers JSON. Use this when you have completed the analysis."""
        return markers

    return [get_existing_threads, search_nodes, output_thread_markers]


class Agent2ThreadMarker:
    """Agent2: 使用LangChain Agent进行叙事线标记"""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id
        self.thread_state = ThreadState()

        self.book_repository = BookRepository()
        
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        
        if api_key:
            self.llm = create_llm(api_key=api_key, temperature=0.3, api_base=api_base)
        else:
            self.llm = None

    def _create_agent(self):
        """Create a LangChain agent for thread marking."""
        tools = create_thread_tools(self.book_id) if self.book_id else []
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a narrative structure analyst. Your task is to assign thread markers to narrative nodes.

For each node, determine:
- thread_id: Which thread this node belongs to (main or thread_N)
- thread_name: Name of the thread
- thread_prev_node_id: The previous node in the same thread (if any)

Rules:
1. Nodes with the same main characters should be in the same thread
2. If characters from a previous thread appear again, continue that thread
3. If new characters appear without previous context, start a new thread
4. Always link to the last node of the same thread for continuity

Output format: JSON array with node_id, thread_id, thread_name, thread_prev_node_id, thread_next_node_id"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessage(content="""Analyze these nodes and assign thread markers:

Nodes:
{nodes}

Recent context (for continuity):
{context}

Output your final answer using the output_thread_markers tool."""),
        ])

        return create_agent(self.llm, tools, prompt=prompt)

    async def mark(self, nodes: list[dict], context: dict | None = None) -> list[dict]:
        """Mark nodes with thread information."""
        if not nodes:
            return []
        
        debug_log("agent2", "Agent2ThreadMarker.mark called with {} nodes", len(nodes))

        if self.llm is None:
            debug_log("agent2", "LLM disabled, using defaults")
            return self._build_with_defaults(nodes)

        context_summary = self.thread_state.get_context_summary()

        try:
            agent_executor = self._create_agent()
            
            result = await agent_executor.ainvoke({
                "nodes": json.dumps(nodes, ensure_ascii=False),
                "context": json.dumps(context_summary, ensure_ascii=False)
            })

            output = result.get("output", "")
            debug_log("agent2", "Agent output: {}", output[:500])

            llm_results = self._parse_results(output)
            
        except Exception as e:
            debug_log("agent2", "Agent execution failed: {}", str(e))
            llm_results = []

        return self._merge_results(nodes, llm_results)

    def _parse_results(self, content: str) -> list:
        """Parse thread markers from agent output."""
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

        logger.warning(f"Failed to parse thread markers from output: {content[:200]}")
        return []

    def _merge_results(self, nodes: list[dict], llm_results: list[dict]) -> list[dict]:
        """合并 LLM 结果，更新 thread 信息"""
        result_map = {r.get("node_id", ""): r for r in llm_results}

        for idx, node in enumerate(nodes):
            node_id = node.get("id", "")
            characters = [c.get("name", "") for c in node.get("characters", []) if c.get("name")]
            llm_hint = result_map.get(node_id, {})

            # 分配 thread_id
            thread_id = self._assign_thread(llm_hint, characters)
            node["thread_id"] = thread_id
            node["thread_name"] = llm_hint.get("thread_name", "")

            # 设置前置节点
            node["thread_prev_node_id"] = self.thread_state.get_last_node(thread_id)
            node["thread_next_node_id"] = ""

            debug_log("agent2", "  node[{}] id={} thread={} prev={}",
                     idx, node_id, thread_id, node["thread_prev_node_id"])

            # 更新 thread state
            self.thread_state.add_thread(thread_id, characters)
            self.thread_state.set_last_node(thread_id, node_id)

        # 设置 next_node_id
        for idx, node in enumerate(nodes[:-1]):
            if node.get("thread_id") == nodes[idx + 1].get("thread_id"):
                node["thread_next_node_id"] = nodes[idx + 1].get("id", "")

        debug_log("agent2", "Final threads: {}", list(self.thread_state.threads.keys()))
        return nodes

    def _assign_thread(self, llm_hint: dict, characters: list[str]) -> str:
        """根据 LLM 提示和角色分配 thread"""
        thread_id = llm_hint.get("thread_id", "")

        if thread_id:
            return thread_id

        if not self.thread_state.threads:
            return "main"

        # 查找最佳匹配的 thread
        src = set(characters)
        best_thread = None
        best_ratio = 0.0
        for tid, thread_chars in self.thread_state.threads.items():
            overlap = len(src & thread_chars)
            ratio = overlap / len(src) if src else 0.0
            if ratio > best_ratio and ratio >= 0.5:
                best_thread = tid
                best_ratio = ratio

        if best_thread:
            return best_thread
        
        return f"thread_{len(self.thread_state.threads)}"

    def _build_with_defaults(self, nodes: list[dict]) -> list[dict]:
        """使用默认值构建"""
        for node in nodes:
            node.setdefault("thread_id", "main")
            node.setdefault("thread_name", "")
            node.setdefault("thread_prev_node_id", "")
            node.setdefault("thread_next_node_id", "")
        return nodes
