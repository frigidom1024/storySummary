import json
import logging
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts.graph_builder_prompt import GRAPH_BUILDER_PROMPT

logger = logging.getLogger("story-summary")


class GraphBuilderResult(BaseModel):
    node_id: str
    thread_hint: str = Field(default="main", description="main/new/uncertain")
    link_confidence: float = 0.5


class ThreadState:
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
            ratio = overlap / len(src)
            if ratio > best_ratio:
                best_thread = thread_id
                best_ratio = ratio
        return best_thread, best_ratio


def create_graph_builder_llm(api_key: str | None = None) -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    kwargs = {"api_key": api_key, "model": model, "temperature": 0.3}
    if api_base:
        kwargs["openai_api_base"] = api_base
    return ChatOpenAI(**kwargs)


class GraphBuilder:
    def __init__(self, api_key: str = None):
        self.llm = create_graph_builder_llm(api_key=api_key) if api_key or os.getenv("DEEPSEEK_API_KEY") else None
        self.thread_state = ThreadState()

    def get_context_summary(self) -> dict:
        recent_nodes = []
        for thread_id, last_node in list(self.thread_state.last_node_in_thread.items())[-5:]:
            recent_nodes.append(
                {
                    "id": last_node,
                    "characters": list(self.thread_state.threads.get(thread_id, set())),
                    "thread_id": thread_id,
                }
            )
        return {
            "recent_nodes": recent_nodes,
            "thread_summaries": {k: list(v) for k, v in self.thread_state.threads.items()},
        }

    async def build(self, nodes: list[dict], time_anchors: list, thread_enabled: bool = True) -> list[dict]:
        if not nodes:
            return []
        if not thread_enabled or self.llm is None:
            return self._build_with_defaults(nodes)

        context = self.get_context_summary()
        prompt = GRAPH_BUILDER_PROMPT.format(
            nodes=json.dumps(nodes, ensure_ascii=False),
            recent_nodes=json.dumps(context["recent_nodes"], ensure_ascii=False),
            thread_summaries=json.dumps(context["thread_summaries"], ensure_ascii=False),
        )
        response = await self.llm.ainvoke(
            [
                SystemMessage(content="You are a narrative structure analyst. Output ONLY JSON array."),
                HumanMessage(content=prompt),
            ]
        )
        content = response.content if getattr(response, "content", None) else "[]"
        try:
            llm_results = json.loads(content)
        except Exception:
            logger.warning("Failed to parse GraphBuilderResult, fallback defaults: %s", content[:200])
            return self._build_with_defaults(nodes)
        return self._merge_with_program(nodes, time_anchors, llm_results)

    def _merge_with_program(self, nodes: list[dict], time_anchors: list, llm_results: list[dict]) -> list[dict]:
        result_map = {r.get("node_id", ""): r for r in llm_results}
        for idx, node in enumerate(nodes):
            node_id = node.get("id", "")
            characters = [c.get("name", "") for c in node.get("characters", []) if c.get("name")]
            time_info = time_anchors[idx] if idx < len(time_anchors) else {}
            if hasattr(time_info, "model_dump"):
                time_info = time_info.model_dump()

            node["timeline_order"] = self._calc_timeline_order(time_info)
            thread_id, thread_hint = self._assign_thread(result_map.get(node_id, {}), characters)
            node["thread_id"] = thread_id
            node["thread_hint"] = thread_hint
            node["thread_prev_node_id"] = self.thread_state.get_last_node(thread_id)

            self.thread_state.add_thread(thread_id, characters)
            self.thread_state.set_last_node(thread_id, node_id)
        return nodes

    def _calc_timeline_order(self, time_info: dict) -> int:
        relative = time_info.get("relative_to_prev", "continue")
        if relative == "jump":
            return -1 if time_info.get("time_type") == "past" else 1
        return 0

    def _assign_thread(self, llm_hint: dict, characters: list[str]) -> tuple[str, str]:
        hint = llm_hint.get("thread_hint", "main")
        if hint == "new" or not self.thread_state.threads:
            return ("main" if not self.thread_state.threads else f"thread_{len(self.thread_state.threads)}"), hint

        best_thread, ratio = self.thread_state.find_best_thread(characters)
        if best_thread and ratio >= 0.5:
            return best_thread, "main"
        return f"thread_{len(self.thread_state.threads)}", hint

    def _build_with_defaults(self, nodes: list[dict]) -> list[dict]:
        for node in nodes:
            node.setdefault("timeline_order", 0)
            node.setdefault("thread_id", "main")
            node.setdefault("thread_hint", "main")
            node.setdefault("thread_prev_node_id", "")
        return nodes
