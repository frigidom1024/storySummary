import json
import logging
import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts.time_anchor import TIME_ANCHOR_PROMPT

logger = logging.getLogger("story-summary")


class TimeAnchorResult(BaseModel):
    node_id: str
    time_type: str = Field(default="present", description="present/past/future")
    relative_to_prev: str = Field(default="continue", description="continue/jump/unclear")
    anchor_hint: str = ""
    confidence: float = 0.5


def create_time_anchor_llm(api_key: str | None = None) -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    kwargs = {"api_key": api_key, "model": model, "temperature": 0.3}
    if api_base:
        kwargs["openai_api_base"] = api_base
    return ChatOpenAI(**kwargs)


class TimeAnchorResolver:
    def __init__(self, api_key: str = None):
        self.llm = create_time_anchor_llm(api_key=api_key) if api_key or os.getenv("DEEPSEEK_API_KEY") else None

    async def resolve(self, nodes: list[dict], last_timeline_state: dict | None = None) -> list[TimeAnchorResult]:
        if not nodes:
            return []

        if self.llm is None:
            return [TimeAnchorResult(node_id=n.get("id", "")) for n in nodes]

        prompt = TIME_ANCHOR_PROMPT.format(
            last_timeline_state=json.dumps(last_timeline_state or {}, ensure_ascii=False),
            nodes=json.dumps(nodes, ensure_ascii=False),
        )
        response = await self.llm.ainvoke(
            [
                SystemMessage(content="You are a time analyst. Output ONLY JSON array."),
                HumanMessage(content=prompt),
            ]
        )
        content = response.content if getattr(response, "content", None) else "[]"
        try:
            return [TimeAnchorResult(**item) for item in json.loads(content)]
        except Exception:
            logger.warning("Failed to parse TimeAnchorResult, fallback to defaults: %s", content[:200])
            return [TimeAnchorResult(node_id=n.get("id", "")) for n in nodes]
