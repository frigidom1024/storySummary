import os
import re
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState, RelationshipStateChange
from src.prompts import MULTI_BEAT_NODE_PROMPT
from src.core.tools.tool_executor import (
    get_previous_chunk_nodes_impl,
    get_thread_last_node_impl,
    search_nodes_impl,
)

logger = logging.getLogger("story-summary")


# ====================== Pydantic Models (for test compatibility) ======================
class CharacterStateModel(BaseModel):
    """Character state schema for structured output."""
    name: str = Field(description="Character name")
    state_before: str = Field(default="", description="Emotional/condition state when entering this scene")


class RelationshipStateChangeModel(BaseModel):
    """Relationship state change schema."""
    pair: str = Field(default="", description="Pair name e.g. '陈屿-沈昭'")
    from_state: str = Field(default="", description="State before")
    to_state: str = Field(default="", description="State after")


class NarrativeBeatModel(BaseModel):
    """Single narrative beat schema - 叙事索引卡."""
    id: str = Field(description="Unique beat ID")
    beat_index: int = Field(description="Position within chunk (0, 1, 2...)")
    scene: str = Field(description="Full scene description e.g. '青岛路旧书店，下午三点多'")
    location: str = Field(default="", description="Simplified location name")
    scene_timing: str = Field(default="", description="Time period: 午后/傍晚/夜间 etc")
    characters: list[CharacterStateModel] = Field(default_factory=list, description="Characters present in this beat")
    situation: str = Field(default="", description="Core situation in one sentence, max 25 chars")
    turning_point: str = Field(default="", description="What changed in this beat, or '渐变：...'")
    emotional_arc: str = Field(default="", description="Emotional arc e.g. '陈屿从[X]到[Y]'")
    mood_tone: str = Field(default="", description="Mood keywords, 3 items comma-separated")
    narrative_rhythm: str = Field(default="", description="slow / steady / fast / pause")
    discussion_prompts: list[str] = Field(default_factory=list, description="Discussion anchors for podcast")
    relationship_delta: list[RelationshipStateChangeModel] = Field(default_factory=list, description="Relationship changes in this beat")
    narrative_role: str = Field(default="", description="opening / rising / climax / ending")

    # === 时间坐标 ===
    timeline_order: int = Field(default=0, description="Story-chronological order: negative=before主线, positive=after主线")
    timeline_anchor: str = Field(default="", description="Time anchor: 大学时期/毕业后一年/现在/第一章 etc")
    is_time_jump: bool = Field(default=False, description="Is this a time jump?")
    jump_direction: str = Field(default="", description="past/future - direction of jump")
    jump_label: str = Field(default="", description="插叙/倒叙/前传/前传 or empty")

    # === 叙事线链路 ===
    thread_id: str = Field(default="main", description="Thread ID: main/zhang/chenwei/laozhou etc")
    thread_name: str = Field(default="", description="Thread display name")
    thread_prev_node_id: str = Field(default="", description="Previous node ID in same thread")
    thread_next_node_id: str = Field(default="", description="Next node ID in same thread (optional)")

    # === 分支/汇聚 ===
    branch_from_node: str = Field(default="", description="Node ID where this thread diverged")
    converges_to_node: str = Field(default="", description="Node ID this thread converges to")
    is_convergence: bool = Field(default=False, description="Is this a multi-thread convergence point?")


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


# ====================== 工具 ======================
def create_node_tools(book_id: str):
    """Create tools bound to a specific book_id."""

    @tool
    def get_previous_chunk_nodes() -> str:
        """Get all nodes from the previous chunk.

        Use this to understand the time anchor (timeline_anchor) of the
        chunk that came before the current one.
        """
        result = get_previous_chunk_nodes_impl(book_id=book_id)
        return json.dumps(result, ensure_ascii=False)

    @tool
    def get_thread_last_node(thread_id: str) -> str:
        """Get the last (newest) node in a given thread's chain.

        Args:
            thread_id: e.g. 'main', 'zhang', 'chenwei', 'laozhou'
        """
        result = get_thread_last_node_impl(book_id=book_id, thread_id=thread_id)
        if result is None:
            return "null"
        return json.dumps(result, ensure_ascii=False)

    @tool
    def search_nodes(keyword: str) -> str:
        """Search nodes by character name or scene keyword.

        Args:
            keyword: character name to search for
        """
        result = search_nodes_impl(book_id=book_id, keyword=keyword)
        return json.dumps(result, ensure_ascii=False)

    return [get_previous_chunk_nodes, get_thread_last_node, search_nodes]


class NarrativeNodeGenerator:
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

        # Try direct JSON parse first
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and 'beats' in parsed:
                return parsed['beats']
        except json.JSONDecodeError:
            pass

        # Try to extract JSON array from text
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
                        logger.debug(f"Extracted JSON array with {len(parsed)} items")
                        return parsed
                    except json.JSONDecodeError:
                        pass

        # Try reasoning field (qwen-plus model)
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

        # Ensure defaults
        beat_dict.setdefault('location', '')
        beat_dict.setdefault('scene_timing', '')
        beat_dict.setdefault('characters', [])
        beat_dict.setdefault('situation', '')
        beat_dict.setdefault('turning_point', '')
        beat_dict.setdefault('emotional_arc', '')
        beat_dict.setdefault('mood_tone', '')
        beat_dict.setdefault('narrative_rhythm', 'steady')
        beat_dict.setdefault('discussion_prompts', [])
        beat_dict.setdefault('relationship_delta', [])
        beat_dict.setdefault('narrative_role', 'rising')
        beat_dict.setdefault('timeline_order', 0)
        beat_dict.setdefault('timeline_anchor', '')
        beat_dict.setdefault('is_time_jump', False)
        beat_dict.setdefault('jump_direction', '')
        beat_dict.setdefault('jump_label', '')
        beat_dict.setdefault('thread_id', 'main')
        beat_dict.setdefault('thread_name', '')
        beat_dict.setdefault('thread_prev_node_id', '')
        beat_dict.setdefault('thread_next_node_id', '')
        beat_dict.setdefault('branch_from_node', '')
        beat_dict.setdefault('converges_to_node', '')
        beat_dict.setdefault('is_convergence', False)

        return beat_dict

    async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
        """Generate narrative beats from ONE chunk using tool calling."""
        if self.llm is None:
            raise ValueError(
                "LLM API Key 未配置。请设置 DEFAULT_API_KEY 和 DEFAULT_API_BASE 环境变量，"
                "或配置 DEEPSEEK_API_KEY / OPENAI_API_KEY 环境变量。"
            )

        prompt = MULTI_BEAT_NODE_PROMPT.format(
            text=chunk.text,
            chunk_order=chunk.order
        )

        logger.debug(f"Calling LLM for chunk {chunk.id} (model: {self.model_name})")

        # Create tools bound to this book_id
        tools = create_node_tools(self.book_id)

        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(tools)

        # Build initial messages
        messages = [
            SystemMessage(content="You are a professional narrative analyst. Use tools to gather context if needed, then output ONLY the JSON array of beats. No explanations, no text before or after the JSON. Start with [ and end with ]."),
            HumanMessage(content=prompt)
        ]

        # Tool call loop with proper message handling
        max_tool_calls = 5
        for call_round in range(max_tool_calls):
            logger.debug(f"LLM call round {call_round + 1}")

            # Invoke LLM
            response = await llm_with_tools.ainvoke(messages)

            # Check if response has tool_calls
            if not hasattr(response, 'tool_calls') or not response.tool_calls:
                # No tool calls - this is the final response
                break

            # Process tool calls and add responses to messages
            for tc in response.tool_calls:
                # Get tool name and arguments
                if isinstance(tc, dict):
                    tc_name = tc.get('name')
                    tc_id = tc.get('id')
                    tc_args = tc.get('args', {})
                else:
                    tc_name = getattr(tc, 'name', None)
                    tc_id = getattr(tc, 'id', None)
                    tc_args = getattr(tc, 'args', {})

                if not tc_name:
                    logger.warning(f"Skipping tool call with no name")
                    continue

                # Find and execute the tool
                tool_def = next((t for t in tools if t.name == tc_name), None)
                if not tool_def:
                    logger.warning(f"Tool {tc_name} not found in registry")
                    content = json.dumps({"error": f"unknown tool: {tc_name}"}, ensure_ascii=False)
                else:
                    try:
                        result = tool_def.invoke(tc_args)
                        content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                    except Exception as e:
                        logger.warning(f"Tool {tc_name} failed: {e}")
                        content = json.dumps({"error": str(e)}, ensure_ascii=False)

                # Add tool response as a HumanMessage (not ToolMessage)
                # This is because DeepSeek API expects tool responses as HumanMessage
                tool_msg = HumanMessage(
                    content=content,
                    name=tc_name,
                    tool_call_id=tc_id
                )
                messages.append(tool_msg)

            logger.debug(f"Executed {len(response.tool_calls)} tool(s), continuing...")

        # Get the final response content
        content = ""
        if hasattr(response, 'content') and response.content:
            content = response.content

        # Parse beats from content
        beats_list = self._extract_beats(content)
        logger.debug(f"Extracted {len(beats_list)} beats from response")

        # Convert to NarrativeNode objects
        nodes = []
        for beat_dict in beats_list:
            validated = self._validate_beat(beat_dict)
            if not validated:
                continue

            valid_characters = [
                CharacterState(name=c.get('name', ''), state_before=c.get('state_before', ''))
                for c in validated['characters'] if c.get('name')
            ]

            relationship_delta = [
                RelationshipStateChange(
                    pair=r.get('pair', ''),
                    from_state=r.get('from_state', ''),
                    to_state=r.get('to_state', '')
                )
                for r in validated['relationship_delta'] if r.get('pair')
            ]

            node = NarrativeNode(
                id=validated['id'],
                parent_chunk_id=chunk.id,
                beat_index=validated['beat_index'],
                scene=validated['scene'],
                location=validated['location'],
                scene_timing=validated['scene_timing'],
                characters=valid_characters,
                situation=validated['situation'],
                turning_point=validated['turning_point'],
                emotional_arc=validated['emotional_arc'],
                mood_tone=validated['mood_tone'],
                narrative_rhythm=validated['narrative_rhythm'],
                discussion_prompts=validated['discussion_prompts'],
                relationship_delta=relationship_delta,
                narrative_role=validated['narrative_role'],
                timeline_order=validated['timeline_order'],
                timeline_anchor=validated['timeline_anchor'],
                is_time_jump=validated['is_time_jump'],
                jump_direction=validated['jump_direction'],
                jump_label=validated['jump_label'],
                thread_id=validated['thread_id'],
                thread_name=validated['thread_name'],
                thread_prev_node_id=validated['thread_prev_node_id'],
                thread_next_node_id=validated['thread_next_node_id'],
                branch_from_node=validated['branch_from_node'],
                converges_to_node=validated['converges_to_node'],
                is_convergence=validated['is_convergence'],
            )
            nodes.append(node)

        return nodes
