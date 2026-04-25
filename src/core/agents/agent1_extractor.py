"""Agent1: Narrative Node Extractor - 叙事节点提取"""
import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterStateModel
from src.prompts.base_node import BASE_NODE_PROMPT
from src.logging_config import debug

logger = logging.getLogger("story-summary")


class NarrativeBeatModel(BaseModel):
    """Single narrative beat schema - 叙事索引卡."""
    id: str = Field(description="Unique beat ID")
    beat_index: int = Field(description="Position within chunk (0, 1, 2...)")
    scene: str = Field(description="Full scene description")
    location: str = Field(default="", description="Simplified location name")
    scene_timing: str = Field(default="", description="Time period")
    characters: list[CharacterStateModel] = Field(default_factory=list, description="Characters present")
    event_summary: str = Field(default="", description="Summary of the event")
    situation: str = Field(default="", description="Core situation in one sentence")
    turning_point: str = Field(default="", description="What changed")
    importance: float = Field(default=0.5, description="Node importance 0.0-1.0")
    time_label: str = Field(default="NOW", description="Time label: NOW, PAST, FUTURE")

def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return ChatOpenAI(**llm_kwargs)


def create_node_tools(book_id: str):
    """Create tools for the agent with auto-bound book_id."""
    from src.core.tools.tool_executor import (
        get_previous_chunk_nodes_impl,
    )

    @tool
    def get_previous_chunk_nodes() -> str:
        """Return all nodes from the latest processed chunk.

        Use this tool to understand immediate historical context before generating
        nodes for the current chunk.

        Returns:
            A list of node summaries in JSON format.
            if no previous chunk nodes exist, return an empty list.
        """
        result = get_previous_chunk_nodes_impl(book_id=book_id)
        return json.dumps(result if result else [], ensure_ascii=False)

    @tool
    def output_beats(beats: str) -> str:
        """Output the final JSON array of narrative beats.

        Use this tool when you have completed the analysis and are ready to output
        the final list of narrative beats.

        Args:
            beats: JSON string containing the array of narrative beats

        Returns:
            The input beats string, for confirmation.
        """
        return beats

    return [get_previous_chunk_nodes, output_beats]


class Agent1Extractor:
    """Agent1: 使用LangChain Agent提取叙事节点"""

    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id
        self.model_name = model or os.getenv("LLM_MODEL", "deepseek-chat")
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        
        if api_key:
            self.llm = create_llm(api_key=api_key, model=self.model_name, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

    def _create_agent(self, is_first_chunk: bool):
        """Create a LangChain agent for the extractor."""
        tools = create_node_tools(self.book_id) if self.book_id else []
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a professional narrative analyst. Your task is to extract narrative beats from the provided text.

Extract beats that represent meaningful narrative moments:
- Character changes (entering/leaving)
- Scene transitions
- Emotional turning points or decisions
- Key events or plot twists
- Important character interactions

Output format: JSON array of beats, each beat must have:
- id: beat ID (format n-{chunk_order}-{beat_index})
- beat_index: order within chunk (0, 1, 2...)
- scene: full scene description
- location: simplified location
- scene_timing: time period (午后/傍晚/夜间 etc)
- characters: list of character names
- event_summary: summary of the event
- situation: one sentence describing the current situation (max 25 chars)
- turning_point: what changed in this beat
- importance: importance 0.0-1.0
- time_label: NOW/PAST/FUTURE

Use tools to get context from previous chunks if needed, then output the final JSON using the output_beats tool."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessage(content="""Analyze this text and extract narrative beats:

Text to analyze:
{text}

Chunk order: {chunk_order}

{context_hint}

Output your final answer using the output_beats tool."""),
        ])

        return create_agent(self.llm, tools, prompt=prompt)

    def _validate_beat(self, beat_dict: dict) -> Optional[dict]:
        """Validate and normalize a beat dict."""
        required_fields = ['id', 'beat_index', 'scene']
        for field in required_fields:
            if field not in beat_dict or beat_dict[field] is None:
                logger.warning(f"Beat missing required field '{field}': {beat_dict.get('id', 'unknown')}")
                return None

        beat_dict.setdefault('location', '')
        beat_dict.setdefault('scene_timing', '')
        beat_dict.setdefault('characters', [])
        beat_dict.setdefault('event_summary', '')
        beat_dict.setdefault('situation', '')
        beat_dict.setdefault('turning_point', '')
        beat_dict.setdefault('importance', 0.5)
        beat_dict.setdefault('time_label', 'NOW')
        beat_dict.setdefault('thread_id', 'main')
        beat_dict.setdefault('thread_name', '')
        beat_dict.setdefault('thread_prev_node_id', '')
        beat_dict.setdefault('thread_next_node_id', '')
        beat_dict.setdefault('discussion_prompts', [])

        try:
            beat_dict['importance'] = max(0.0, min(1.0, float(beat_dict['importance'])))
        except (TypeError, ValueError):
            beat_dict['importance'] = 0.5

        return beat_dict

    async def extract(self, chunk: Chunk) -> list[dict]:
        """Extract narrative beats from a chunk using LangChain Agent."""
        if self.llm is None:
            raise ValueError("LLM API Key 未配置。请设置 DEEPSEEK_API_KEY 环境变量。")

        debug("agent1", "[Chunk {}] Starting extraction with LangChain Agent", chunk.id)

        is_first_chunk = chunk.order == 0
        context_hint = "" if is_first_chunk else "You may use tools to get context from previous chunks."

        try:
            agent_executor = self._create_agent(is_first_chunk)
            
            result = await agent_executor.ainvoke({
                "text": chunk.text,
                "chunk_order": chunk.order,
                "context_hint": context_hint
            })

            output = result.get("output", "")
            debug("agent1", "[Chunk {}] Agent output: {}", chunk.id, output[:500])

            beats_list = self._parse_beats(output)
            
        except Exception as e:
            debug("agent1", "[Chunk {}] Agent execution failed: {}", chunk.id, str(e))
            beats_list = []

        validated_beats = []
        for beat_dict in beats_list:
            validated = self._validate_beat(beat_dict)
            if validated:
                validated_beats.append(validated)

        debug("agent1", "[Chunk {}] Validated {} beats", chunk.id, len(validated_beats))
        return validated_beats

    def _parse_beats(self, content: str) -> list:
        """Parse beats from agent output."""
        import re
        
        if not content:
            return []

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and 'beats' in parsed:
                return parsed['beats']
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'\[\s*\{[^}\]]*"id"\s*:[^}\]]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse beats from output: {content[:200]}")
        return []
