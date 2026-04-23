"""Agent1: Narrative Node Extractor - 叙事节点提取"""
import os
import re
import json
import logging
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState, RelationshipStateChange, InteractionModel
from src.prompts.base_node import BASE_NODE_PROMPT
from src.logging_config import debug

logger = logging.getLogger("story-summary")


class CharacterStateModel(BaseModel):
    """Character state schema for structured output."""
    name: str = Field(description="Character name")


class RelationshipStateChangeModel(BaseModel):
    """Relationship state change schema."""
    pair: str = Field(default="", description="Pair name e.g. '陈屿-沈昭'")
    from_state: str = Field(default="", description="State before")
    to_state: str = Field(default="", description="State after")


class InteractionModelCompat(BaseModel):
    """Interaction schema for compatibility."""
    target: str = Field(default="", description="Target character name")
    type: str = Field(default="neutral", description="tension/support/neutral")
    intensity_delta: float = Field(default=0.0, description="-1.0 to 1.0")


class NarrativeBeatModel(BaseModel):
    """Single narrative beat schema - 叙事索引卡."""
    #agent1_extractor fields
    id: str = Field(description="Unique beat ID")
    beat_index: int = Field(description="Position within chunk (0, 1, 2...)")
    scene: str = Field(description="Full scene description e.g. '青岛路旧书店，下午三点多'")
    location: str = Field(default="", description="Simplified location name")
    scene_timing: str = Field(default="", description="Time period: 午后/傍晚/夜间 etc")
    characters: list[CharacterStateModel] = Field(default_factory=list, description="Characters present in this beat")
    event_summary: str = Field(default="", description="Summary of the event in this beat")
    situation: str = Field(default="", description="Core situation in one sentence, max 25 chars")
    turning_point: str = Field(default="", description="What changed in this beat, or '渐变：...'")
    importance: float = Field(default=0.5, description="Node importance 0.0-1.0 for visualization node size")
    time_label: str = Field(default="", description="Time label: NOW, PAST, FUTURE")



    #agent_time_marker fields
    thread_id: str = Field(default="", description="Thread ID: main/zhang/chenwei/laozhou etc")
    thread_name: str = Field(default="", description="Thread name")
    thread_prev_node_id: str = Field(default="", description="Previous node ID in same thread")
    thread_next_node_id: str = Field(default="", description="Next node ID in same thread (optional)")

    #agent_intresting_finder fields
    discussion_prompts: list[str] = Field(default_factory=list, description="Discussion anchors for podcast")


class NarrativeBeatsOutput(BaseModel):
    """Output schema for multiple narrative beats."""
    beats: list[NarrativeBeatModel] = Field(default_factory=list, description="List of narrative beats")


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client with DeepSeek, OpenAI, or DashScope compatibility."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")

    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

    return ChatOpenAI(**llm_kwargs)


# ====================== Tools ======================
def create_node_tools(book_id: str, is_first_chunk: bool = False):
    """Create tools bound to a specific book_id."""

    from src.core.tools.tool_executor import (
        get_previous_chunk_nodes_impl,
        get_thread_last_node_impl,
        search_nodes_impl,
    )

    @tool
    def get_previous_chunk_nodes() -> str:
        """Get all nodes from the previous chunk to understand timeline continuity."""
        result = get_previous_chunk_nodes_impl(book_id=book_id)
        if not result:
            return "[]"
        return json.dumps(result, ensure_ascii=False)

    @tool
    def get_thread_last_node(thread_id: str) -> str:
        """Get the last (newest) node in a given character's storyline thread."""
        result = get_thread_last_node_impl(book_id=book_id, thread_id=thread_id)
        if result is None:
            return "null"
        return json.dumps(result, ensure_ascii=False)

    @tool
    def search_nodes(keyword: str) -> str:
        """Search previously analyzed nodes by character name or scene keyword."""
        result = search_nodes_impl(book_id=book_id, keyword=keyword)
        return json.dumps(result, ensure_ascii=False)

    tools = []
    if not is_first_chunk:
        tools.append(get_previous_chunk_nodes)
    tools.extend([get_thread_last_node, search_nodes])

    return tools


class Agent1Extractor:
    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id
        self.model_name = model or os.getenv("LLM_MODEL", "deepseek-chat")

        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            self.llm = create_llm(api_key=api_key, model=self.model_name, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

    def _extract_beats(self, content: str) -> list:
        """Extract JSON beats list from response content."""
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
            start = json_match.start()
            depth = 0
            for i, c in enumerate(content[start:]):
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(content[start:start+i+1])
                        debug("agent1", "Extracted JSON array with {} items", len(parsed))
                        return parsed
                    except json.JSONDecodeError:
                        pass

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and 'reasoning' in parsed:
                reasoning_text = parsed['reasoning']
                json_match = re.search(r'\[\s*\{\s*"id"\s*:', reasoning_text)
                if json_match:
                    start_idx = json_match.start()
                    depth = 0
                    end_idx = start_idx
                    for i, c in enumerate(reasoning_text[start_idx:]):
                        if c == '[':
                            depth += 1
                        elif c == ']':
                            depth -= 1
                        if depth == 0:
                            end_idx = start_idx + i + 1
                            break
                    json_str = reasoning_text[start_idx:end_idx]
                    return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        logger.warning(f"Failed to extract beats from response: {content[:200]}")
        return []

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
        beat_dict.setdefault('emotional_arc', '')
        beat_dict.setdefault('mood_tone', '')
        beat_dict.setdefault('narrative_rhythm', 'steady')
        beat_dict.setdefault('discussion_prompts', [])
        beat_dict.setdefault('relationship_delta', [])
        beat_dict.setdefault('interactions', [])
        beat_dict.setdefault('time_label', '')
        beat_dict.setdefault('thread_id', 'main')
        beat_dict.setdefault('thread_name', '')
        beat_dict.setdefault('thread_prev_node_id', '')
        beat_dict.setdefault('thread_next_node_id', '')

        try:
            beat_dict['importance'] = float(beat_dict['importance'])
        except (TypeError, ValueError):
            beat_dict['importance'] = 0.5
        beat_dict['importance'] = max(0.0, min(1.0, beat_dict['importance']))

        return beat_dict

    async def extract(self, chunk: Chunk) -> list[dict]:
        """Extract narrative beats from a chunk using LLM with tool calling."""
        if self.llm is None:
            raise ValueError(
                "LLM API Key 未配置。请设置 DEFAULT_API_KEY 和 DEFAULT_API_BASE 环境变量，"
                "或配置 DEEPSEEK_API_KEY / OPENAI_API_KEY 环境变量。"
            )

        prompt = BASE_NODE_PROMPT.format(
            text=chunk.text,
            chunk_order=chunk.order,
            last_nodes="",
            beat_index=0
        )

        debug("agent1", "Calling LLM for chunk {} model={}", chunk.id, self.model_name)

        is_first_chunk = chunk.order == 0
        tools = create_node_tools(self.book_id, is_first_chunk=is_first_chunk)
        llm_with_tools = self.llm.bind_tools(tools)

        system_prompt = (
            "You are a professional narrative analyst. Your task is to extract narrative beats (beats) from the provided text. "
            "Output ONLY a JSON array of beats. Start with [ and end with ]. No explanations, no text before or after.\n\n"
            "IMPORTANT decision rules for tool usage:\n"
            "1. If this is the first chunk (order=0) or you have sufficient context from the current text: DO NOT call any tools. Just analyze and output JSON.\n"
            "2. Only call tools when: you need to check character history from previous chunks, or you cannot identify a character/location in current text.\n"
            "3. If you call a tool and get [ ] or null back: Stop calling tools and proceed with analysis using ONLY the current text.\n"
            "4. Do NOT repeatedly call the same tool expecting different results."
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]

        max_tool_calls = 4
        debug("agent1", "[Chunk {}] Starting analysis, is_first_chunk={}, max_tool_calls={}", chunk.id, is_first_chunk, max_tool_calls)

        for call_round in range(max_tool_calls):
            debug("agent1", "[Round {}/{}] Sending request with {} messages", call_round + 1, max_tool_calls, len(messages))

            response = await llm_with_tools.ainvoke(messages)

            content = response.content if hasattr(response, 'content') and response.content else ""
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls

            debug("agent1", "[Round {}] Response: has_content={}, has_tool_calls={}, content_len={}",
                  call_round + 1, bool(content), bool(has_tool_calls), len(content))

            if content and not has_tool_calls:
                debug("agent1", "[Round {}] LLM decided to output JSON directly (no tools called)", call_round + 1)
                debug("agent1", "[Round {}] Content preview: {}", call_round + 1, content[:300])
            elif has_tool_calls:
                debug("agent1", "[Round {}] LLM decided to call {} tool(s): {}",
                      call_round + 1, len(response.tool_calls),
                      [tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None) for tc in response.tool_calls])

            if not has_tool_calls:
                debug("agent1", "[Round {}] No tool calls - LLM will output JSON", call_round + 1)
                break

            for tc in response.tool_calls:
                if isinstance(tc, dict):
                    tc_name = tc.get('name')
                    tc_id = tc.get('id')
                    tc_args = tc.get('args', {})
                else:
                    tc_name = getattr(tc, 'name', None)
                    tc_id = getattr(tc, 'id', None)
                    tc_args = getattr(tc, 'args', {})

                if not tc_name:
                    debug("agent1", "[Round {}] Skipping tool call with no name", call_round + 1)
                    continue

                debug("agent1", "[Round {}] → Calling tool: {} args={}", call_round + 1, tc_name, tc_args)

                tool_def = next((t for t in tools if t.name == tc_name), None)
                if not tool_def:
                    debug("agent1", "[Round {}] Tool {} not found", call_round + 1, tc_name)
                    tool_result = json.dumps({"error": f"unknown tool: {tc_name}"}, ensure_ascii=False)
                else:
                    try:
                        tool_result = tool_def.invoke(tc_args)
                        tool_result_str = tool_result if isinstance(tool_result, str) else json.dumps(tool_result, ensure_ascii=False)
                        debug("agent1", "[Round {}] → Tool {} returned (len={}): {}...",
                              call_round + 1, tc_name, len(tool_result_str), tool_result_str[:150])
                        tool_result = tool_result_str
                    except Exception as e:
                        debug("agent1", "[Round {}] Tool {} failed: {}", call_round + 1, tc_name, e)
                        tool_result = json.dumps({"error": str(e)}, ensure_ascii=False)

                tool_msg = HumanMessage(
                    content=tool_result,
                    name=tc_name,
                    tool_call_id=tc_id
                )
                messages.append(tool_msg)

            debug("agent1", "Executed {} tool(s), continuing", len(response.tool_calls))

        final_content = ""
        if hasattr(response, 'content') and response.content:
            final_content = response.content
            debug("agent1", "Final response content length={}", len(final_content))

        beats_list = self._extract_beats(final_content)
        debug("agent1", "Extracted {} beats from LLM", len(beats_list))
        if beats_list:
            debug("agent1", "Sample beat[0]: {}", beats_list[0])

        validated_beats: list[dict] = []
        for beat_dict in beats_list:
            validated = self._validate_beat(beat_dict)
            if not validated:
                continue
            validated_beats.append(validated)

        debug("agent1", "Agent1: Validated {} beats", len(validated_beats))
        for i, vb in enumerate(validated_beats):
            debug("agent1", "  beat[{}] id={} scene={} chars={} time_label={} thread_id={}",
                  i, vb.get('id'), vb.get('scene', '')[:30], len(vb.get('characters', [])),
                  vb.get('time_label'), vb.get('thread_id'))

        return validated_beats
