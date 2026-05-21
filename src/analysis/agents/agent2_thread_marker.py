"""Agent2: Thread Marker - 叙事线标记"""
import json
import logging
import os
import re
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from src.storage.book_repository import BookRepository
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


@tool
def search_nodes(keyword: str, book_id: str = None) -> str:
    """Search nodes by character name or keyword."""
    from src.analysis.tools.tool_executor import search_nodes_impl
    result = search_nodes_impl(book_id=book_id, keyword=keyword) if book_id else []
    return json.dumps(result, ensure_ascii=False)


class Agent2ThreadMarker:
    """Agent2: 使用LangChain Agent进行叙事线标记"""

    SYSTEM_PROMPT = """You are a narrative structure analyst. Your task is to assign thread markers to narrative nodes.

For each node, determine:
- thread_id: Which thread this node belongs to (main or thread_N)
- thread_name: Name of the thread
- thread_prev_node_id: The previous node in the same thread (if any)

Rules:
1. MOST nodes should be in the "main" thread - only create new threads when there are significant character/plot divergences
2. Nodes with the same main characters should be in the same thread
3. If characters from a previous thread appear again, continue that thread
4. If new characters appear without previous context, start a new thread ONLY if they form a distinct subplot
5. Always link to the last node of the same thread for continuity

You can use search_nodes to find related nodes by character name.

IMPORTANT: Output ONLY the JSON array in your response, no explanation."""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id
        self.book_repository = BookRepository()

        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            self.llm = create_llm(api_key=api_key, temperature=0.3, api_base=api_base)
        else:
            self.llm = None

        self.tools = [search_nodes]

    def _create_agent(self):
        """Create a LangChain agent for thread marking."""
        from langchain.agents import create_agent

        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT
        )

    def _get_existing_threads_info(self) -> dict:
        """从 BookRepository 获取已存在的线程信息"""
        if not self.book_id:
            return {"threads": {}}

        nodes = self.book_repository.load_nodes(self.book_id)
        threads = {}

        for node in nodes:
            thread_id = node.thread_id or "main"
            if thread_id not in threads:
                threads[thread_id] = {
                    "characters": [],
                    "last_nodes": []
                }
            # Add characters
            for char in node.characters:
                if hasattr(char, 'name') and char.name:
                    if char.name not in threads[thread_id]["characters"]:
                        threads[thread_id]["characters"].append(char.name)

        # Get last 3 nodes per thread
        for node in nodes:
            thread_id = node.thread_id or "main"
            if len(threads[thread_id]["last_nodes"]) < 3:
                threads[thread_id]["last_nodes"].append(node.id)

        return {"threads": threads}

    async def mark(self, nodes: list[dict], context: dict | None = None) -> list[dict]:
        """Mark nodes with thread information."""
        if not nodes:
            return []

        debug_log("agent2", "Agent2ThreadMarker.mark called with {} nodes", len(nodes))

        if self.llm is None:
            debug_log("agent2", "LLM disabled, using defaults")
            return self._build_with_defaults(nodes)

        # 从 BookRepository 获取已有线程信息
        existing_info = self._get_existing_threads_info()
        existing_threads = existing_info.get("threads", {})

        try:
            agent_executor = self._create_agent()

            user_message = f"""Analyze these nodes and assign thread markers.

EXISTING THREADS (with characters and recent nodes):
{json.dumps(existing_threads, ensure_ascii=False, indent=2)}

If a node's characters match an existing thread, continue that thread.
Only create a new thread (thread_N) if characters don't match any existing thread.
Most nodes should be in the "main" thread.

Nodes:
{json.dumps(nodes, ensure_ascii=False)}

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

            debug_log("agent2", "Agent output: {}", str(output)[:500])

            llm_results = self._parse_results(output)

            if not llm_results and output:
                logger.warning(f"Failed to parse thread markers from output: {output[:200]}")

        except Exception as e:
            debug_log("agent2", "Agent execution failed: {}", str(e))
            llm_results = []

        return self._merge_results(nodes, llm_results, existing_threads)

    def _parse_results(self, content: str) -> list:
        """Parse thread markers from agent output."""
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

        json_match = re.search(r'\[\s*\{[^}\]]*"node_id"\s*:[^}\]]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse thread markers from output: {content[:200]}")
        return []

    def _merge_results(self, nodes: list[dict], llm_results: list[dict], existing_threads: dict) -> list[dict]:
        """合并 LLM 结果，更新 thread 信息"""
        result_map = {r.get("node_id", ""): r for r in llm_results}

        # Get last node per thread from existing threads
        last_nodes = {}
        for thread_id, info in existing_threads.items():
            last_nodes_list = info.get("last_nodes", [])
            if last_nodes_list:
                last_nodes[thread_id] = last_nodes_list[-1]

        for idx, node in enumerate(nodes):
            node_id = node.get("id", "")
            # Handle both string and dict character formats
            raw_characters = node.get("characters", [])
            characters = []
            for c in raw_characters:
                if isinstance(c, str):
                    characters.append(c)
                elif isinstance(c, dict):
                    name = c.get("name", "")
                    if name:
                        characters.append(name)
            llm_hint = result_map.get(node_id, {})

            # 分配 thread_id
            thread_id = self._assign_thread(llm_hint, characters, existing_threads)
            node["thread_id"] = thread_id
            node["thread_name"] = llm_hint.get("thread_name", "")

            # 设置前置节点
            node["thread_prev_node_id"] = last_nodes.get(thread_id, "")
            node["thread_next_node_id"] = ""

            debug_log("agent2", "  node[{}] id={} thread={} prev={}",
                     idx, node_id, thread_id, node["thread_prev_node_id"])

            # 更新 last_nodes
            last_nodes[thread_id] = node_id

        # 设置 next_node_id
        for idx, node in enumerate(nodes[:-1]):
            if node.get("thread_id") == nodes[idx + 1].get("thread_id"):
                node["thread_next_node_id"] = nodes[idx + 1].get("id", "")

        debug_log("agent2", "Final threads: {}", list(set(n.get("thread_id", "main") for n in nodes)))
        return nodes

    def _assign_thread(self, llm_hint: dict, characters: list[str], existing_threads: dict) -> str:
        """根据 LLM 提示和角色分配 thread"""
        thread_id = llm_hint.get("thread_id", "")

        # Validate thread_id - only use if it exists in existing_threads OR is "main"
        if thread_id and thread_id != "main" and thread_id not in existing_threads:
            thread_id = ""  # Force reassignment

        if thread_id:
            return thread_id

        if not existing_threads:
            return "main"

        # 查找最佳匹配的 thread
        src = set(characters)
        if not src:
            return "main"

        best_thread = None
        best_ratio = 0.0
        for tid, info in existing_threads.items():
            thread_chars = set(info.get("characters", []))
            if not thread_chars:
                continue
            overlap = len(src & thread_chars)
            ratio = overlap / len(src) if src else 0.0
            if ratio > best_ratio and ratio >= 0.5:
                best_thread = tid
                best_ratio = ratio

        if best_thread:
            return best_thread

        return "main"

    def _build_with_defaults(self, nodes: list[dict]) -> list[dict]:
        """使用默认值构建"""
        for node in nodes:
            node.setdefault("thread_id", "main")
            node.setdefault("thread_name", "")
            node.setdefault("thread_prev_node_id", "")
            node.setdefault("thread_next_node_id", "")
        return nodes