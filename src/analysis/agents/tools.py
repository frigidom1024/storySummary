"""Agent Tools - Agent2-4 共用的工具函数"""
import json
import logging
from typing import Callable
from langchain_core.tools import tool
from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class AgentTools:
    """Agent2-4 使用的工具集合"""

    def __init__(self, book_id: str = None):
        self.book_id = book_id
        self._search_fn: Callable | None = None
        self._get_thread_last_fn: Callable | None = None

    def set_search_fn(self, fn: Callable) -> None:
        """设置搜索函数"""
        self._search_fn = fn

    def set_get_thread_last_fn(self, fn: Callable) -> None:
        """设置获取线程最后节点函数"""
        self._get_thread_last_fn = fn

    @tool
    def search_nodes(self, keyword: str) -> str:
        """搜索历史节点

        用于查找包含特定角色名或场景关键词的历史节点。
        当你需要了解某个角色之前做了什么，或某个场景之前是否出现过时使用。
        """
        if not self._search_fn:
            return "[]"
        result = self._search_fn(keyword)
        debug_log("agent_tools", "search_nodes keyword={} results={}", keyword, len(result) if result else 0)
        return json.dumps(result, ensure_ascii=False) if result else "[]"

    @tool
    def get_thread_last_node(self, thread_id: str) -> str:
        """获取指定叙事线的最后一个节点

        用于获取某个角色线/支线的最新状态，了解该线之前的发展。
        """
        if not self._get_thread_last_fn:
            return "null"
        result = self._get_thread_last_fn(thread_id)
        debug_log("agent_tools", "get_thread_last_node thread_id={}", thread_id)
        return json.dumps(result, ensure_ascii=False) if result else "null"

    @tool
    def get_thread_history(self, thread_id: str, limit: int = 5) -> str:
        """获取指定叙事线的历史节点列表

        用于了解某个叙事线的完整发展脉络。
        """
        if not self._search_fn:
            return "[]"
        # 使用搜索函数查找该线程的历史节点
        result = self._search_fn(f"thread:{thread_id}")
        if result and isinstance(result, list):
            result = result[:limit]
        debug_log("agent_tools", "get_thread_history thread_id={} limit={} results={}",
                  thread_id, limit, len(result) if result else 0)
        return json.dumps(result, ensure_ascii=False) if result else "[]"

    @tool
    def get_character_appearances(self, character_name: str, limit: int = 3) -> str:
        """获取角色在历史中的登场记录

        用于了解某个角色之前的出场情况和状态变化。
        """
        if not self._search_fn:
            return "[]"
        result = self._search_fn(f"character:{character_name}")
        if result and isinstance(result, list):
            result = result[:limit]
        debug_log("agent_tools", "get_character_appearances name={} limit={} results={}",
                  character_name, limit, len(result) if result else 0)
        return json.dumps(result, ensure_ascii=False) if result else "[]"

    def get_tools(self):
        """获取工具列表"""
        return [
            self.search_nodes,
            self.get_thread_last_node,
            self.get_thread_history,
            self.get_character_appearances,
        ]
