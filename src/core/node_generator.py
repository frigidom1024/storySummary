import json
import re
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState
from src.core.prompts import MULTI_BEAT_NODE_PROMPT


def create_llm(api_key: str = None, model: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client with DeepSeek or OpenAI compatibility."""
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE") or os.getenv("OPENAI_API_BASE")

    model = model or os.getenv("LLM_MODEL", "deepseek-chat")

    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base

    return ChatOpenAI(**llm_kwargs)


class NarrativeNodeGenerator:
    def __init__(self, api_key: str = None, model: str = None):
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")
        self.llm = create_llm(api_key=api_key, model=self.model, temperature=0.7, max_tokens=2000)

    async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
        """Generate MULTIPLE narrative beats from ONE chunk."""
        prompt = MULTI_BEAT_NODE_PROMPT.format(
            text=chunk.text,
            chunk_order=chunk.order
        )

        messages = [
            SystemMessage(content="You are a narrative analyst that outputs valid JSON array."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()

        # Try to extract JSON array from markdown code blocks or raw content
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Failed to parse LLM response as JSON: {content[:200]}")

        # Ensure we always return a list (even for single beat)
        if isinstance(data, dict):
            data = [data]

        nodes = []
        for beat_data in data:
            node = NarrativeNode(
                id=beat_data.get("id", f"n-{chunk.id}-{beat_data.get('beat_index', 0)}"),
                parent_chunk_id=chunk.id,
                beat_index=beat_data.get("beat_index", 0),
                scene=beat_data.get("scene", ""),
                characters=[CharacterState(**c) for c in beat_data.get("characters", [])],
                event=beat_data.get("event", ""),
                dialogue_summary=beat_data.get("dialogue_summary", ""),
                tension=beat_data.get("tension", ""),
                stakes=beat_data.get("stakes", ""),
                foreshadow=beat_data.get("foreshadow", ""),
                narrative_role=beat_data.get("narrative_role", "")
            )
            nodes.append(node)

        return nodes
