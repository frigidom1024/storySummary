import os
import re
import json
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState, RelationshipStateChange
from src.core.prompts import MULTI_BEAT_NODE_PROMPT
from src.core.tools.node_query_tools import get_previous_chunk_nodes, get_thread_last_node, search_nodes
from src.core.tools.tool_executor import TOOL_REGISTRY
from langchain_core.messages import ToolMessage

logger = logging.getLogger("story-summary")


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client with DeepSeek, OpenAI, or DashScope compatibility."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")

    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base

    return ChatOpenAI(**llm_kwargs)


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


class NarrativeNodeGenerator:
    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id  # injected externally by pipeline
        self.model_name = model or os.getenv("LLM_MODEL", "deepseek-chat")

        # 优先使用传入的 api_key，其次环境变量
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            self.llm = create_llm(api_key=api_key, model=self.model_name, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

        # Use JsonOutputParser which works with DeepSeek via prompt-based approach
        self.output_parser = JsonOutputParser(pydantic_schema=NarrativeBeatsOutput)

    async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
        """Generate MULTIPLE narrative beats from ONE chunk using structured output + tool calling."""
        if self.llm is None:
            raise ValueError(
                "LLM API Key 未配置。请设置 DEFAULT_API_KEY 和 DEFAULT_API_BASE 环境变量，"
                "或配置 DEEPSEEK_API_KEY / OPENAI_API_KEY 环境变量。"
            )

        prompt = MULTI_BEAT_NODE_PROMPT.format(
            text=chunk.text,
            chunk_order=chunk.order
        )
        format_instructions = self.output_parser.get_format_instructions()
        full_prompt = f"{prompt}\n\n{format_instructions}"

        messages = [
            SystemMessage(content="You are a narrative analyst. Use tools to gather context if needed, then output ONLY the JSON array of beats. No explanations, no text before or after the JSON. Start with [ and end with ]."),
            HumanMessage(content=full_prompt)
        ]

        logger.debug(f"Calling LLM for chunk {chunk.id} (model: {self.model_name})")

        # Bind tools - model may call them before outputting JSON
        llm_with_tools = self.llm.bind_tools(
            [get_previous_chunk_nodes, get_thread_last_node, search_nodes],
            parallel_tool_calls=False
        )

        response = await llm_with_tools.ainvoke(messages)

        # Tool call loop - execute tools and continue
        max_calls = 3
        call_count = 0
        while hasattr(response, 'tool_calls') and response.tool_calls and call_count < max_calls:
            call_count += 1
            # Handle both list of ToolCall objects and list of dicts
            tool_calls = response.tool_calls
            for tc in tool_calls:
                tc_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
                tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                tc_args = tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', {})

                logger.debug(f"Tool call {call_count}: {tc_name} with args: {tc_args}")
                impl = TOOL_REGISTRY.get(tc_name)
                if impl:
                    try:
                        # Always use self.book_id, but pass through other args
                        merged_args = dict(tc_args)
                        merged_args['book_id'] = self.book_id
                        result = impl(**merged_args)
                    except Exception as e:
                        result = {"error": str(e)}
                        logger.warning(f"Tool {tc_name} failed: {e}")
                else:
                    result = {"error": f"unknown tool: {tc_name}"}
                messages.append(ToolMessage(
                    name=tc_name,
                    content=json.dumps(result, ensure_ascii=False),
                    tool_call_id=tc_id
                ))
            response = await llm_with_tools.ainvoke(messages)

        if hasattr(response, 'tool_calls') and response.tool_calls and call_count >= max_calls:
            logger.warning(f"Max tool calls ({max_calls}) reached, proceeding with response")

        try:
            parsed = self.output_parser.parse(response.content)
        except Exception as e:
            # Try to extract JSON from response that has thinking text before JSON
            logger.debug(f"Initial parse failed: {e}, trying to extract JSON from response")
            content = response.content if hasattr(response, 'content') else str(response)
            json_match = re.search(r'\[\s*\{[^}\]]*"id"\s*:[^}\]]*\}', content)
            if json_match:
                # Found potential JSON, try to extract full array
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
                            logger.debug(f"Successfully extracted JSON array with {len(parsed)} items")
                            break
                        except:
                            pass
                else:
                    parsed = None
            if parsed is None:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                return []

        # parsed can be a list directly or dict with 'beats' key
        # Handle qwen-plus reasoning field case
        if parsed is None:
            beats_list = []
        elif isinstance(parsed, list):
            beats_list = parsed
        else:
            beats_list = parsed.get('beats', [])

        # If beats_list is empty but we have a 'reasoning' field, try to extract JSON from it
        if not beats_list and isinstance(parsed, dict) and 'reasoning' in parsed:
            reasoning_text = parsed['reasoning']
            logger.debug(f"Found reasoning field, attempting to extract JSON from it (first 300 chars): {reasoning_text[:300]}")
            # Try to find JSON array containing beats - look for pattern starting with [{"id":
            json_match = re.search(r'\[\s*\{\s*"id"\s*:', reasoning_text)
            if json_match:
                # Found start of JSON array, now find the matching closing bracket
                start_idx = json_match.start()
                # Count brackets to find the matching end
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
                logger.debug(f"Extracted JSON candidate (first 100 chars): {json_str[:100]}")
                try:
                    beats_list = json.loads(json_str)
                    logger.debug(f"Successfully extracted {len(beats_list)} beats from reasoning")
                except Exception as e:
                    logger.debug(f"Failed to parse JSON from reasoning: {e}, json_str: {json_str[:100]}")
        logger.debug(f"Parsed response: {str(parsed)[:300]}, beats_list length: {len(beats_list)}")

        nodes = []
        for beat_dict in beats_list:
            try:
                beat_data = NarrativeBeatModel.model_validate(beat_dict)
            except Exception:
                logger.warning(f"Skipping invalid beat: {beat_dict.get('id', 'unknown')}")
                continue

            valid_characters = [
                CharacterState(name=c.name, state_before=c.state_before)
                for c in beat_data.characters if c.name
            ]

            node = NarrativeNode(
                id=beat_data.id,
                parent_chunk_id=chunk.id,
                beat_index=beat_data.beat_index,
                scene=beat_data.scene,
                location=beat_data.location,
                scene_timing=beat_data.scene_timing,
                characters=valid_characters,
                situation=beat_data.situation,
                turning_point=beat_data.turning_point,
                emotional_arc=beat_data.emotional_arc,
                mood_tone=beat_data.mood_tone,
                narrative_rhythm=beat_data.narrative_rhythm,
                discussion_prompts=beat_data.discussion_prompts,
                relationship_delta=[
                    RelationshipStateChange(pair=r.pair, from_state=r.from_state, to_state=r.to_state)
                    for r in beat_data.relationship_delta if r.pair
                ],
                narrative_role=beat_data.narrative_role,
                timeline_order=beat_data.timeline_order,
                timeline_anchor=beat_data.timeline_anchor,
                is_time_jump=beat_data.is_time_jump,
                jump_direction=beat_data.jump_direction,
                jump_label=beat_data.jump_label,
                thread_id=beat_data.thread_id or "main",
                thread_name=beat_data.thread_name,
                thread_prev_node_id=beat_data.thread_prev_node_id,
                thread_next_node_id=beat_data.thread_next_node_id,
                branch_from_node=beat_data.branch_from_node,
                converges_to_node=beat_data.converges_to_node,
                is_convergence=beat_data.is_convergence,
            )
            nodes.append(node)

        return nodes
