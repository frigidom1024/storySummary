"""Agent1: Narrative Node Extractor - 叙事节点提取"""
import json
import logging
import os
import re
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterStateModel
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


class Agent1Extractor:
    """Agent1: 使用直接LLM调用提取叙事节点"""

    SYSTEM_PROMPT = """You are a professional narrative analyst. Your task is to extract narrative beats from the provided text.

Extract beats that represent meaningful narrative moments:
- Character changes (entering/leaving)
- Scene transitions
- Emotional turning points or decisions
- Key events or plot twists
- Important character interactions

Output format: JSON array of beats, each beat must have:
- beat_index: order within chunk (0, 1, 2...)
- scene: vivid scene description with specific sensory details and actions (describe what actually happens, not summary)
- location: simplified location
- scene_timing: time period (午后/傍晚/夜间 etc)
- characters: list of character names (MUST use the exact names from known characters list)
- event_summary: what happened in this beat
- situation: one sentence describing the current situation (max 25 chars)
- turning_point: what changed in this beat
- importance: importance 0.0-1.0 (0.9-1.0 for major plot turns, 0.7-0.8 for key events, 0.5-0.6 for transitional scenes, below 0.5 for minor beats)
- time_label: NOW/PAST/FUTURE

IMPORTANT:
- Use EXACT character names from the known characters list below
- NEVER use "主人公" or "主角" - use the actual character name
- scene should be VIVID and DESCRIPTIVE, not summary: describe specific actions, expressions, dialogue snippets
- Output ONLY the JSON array in your response, no explanation."""

    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id
        self.model_name = model or os.getenv("LLM_MODEL", "deepseek-chat")
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            self.llm = create_llm(api_key=api_key, model=self.model_name, temperature=0.7, api_base=api_base)
        else:
            self.llm = None

    def get_known_characters_context(self) -> str:
        """获取已知角色的详细信息，用于 AI 参考"""
        if not self.book_id:
            return ""
        try:
            from src.storage.book_repository import book_repository
            characters = book_repository.load_characters(self.book_id)
            if not characters:
                return ""

            lines = ["Known characters in this book:"]
            for name, card in characters.items():
                first_seen = f"(first seen: {card.first_seen_scene[:30]}...)" if card.first_seen_scene else ""
                rels = []
                for target, rel in card.relationships.items():
                    rels.append(f"{target}({rel.type})")
                rel_str = f", relations: {', '.join(rels)}" if rels else ""
                lines.append(f"- {name} {first_seen}{rel_str}")
            return "\n".join(lines)
        except Exception:
            return ""

    def _validate_beat(self, beat_dict: dict, chunk_order: int) -> Optional[dict]:
        """Validate and normalize a beat dict."""
        required_fields = ['beat_index', 'scene']
        for field in required_fields:
            if field not in beat_dict or beat_dict[field] is None:
                logger.warning(f"Beat missing required field '{field}': {beat_dict.get('id', 'unknown')}")
                return None

        # Construct id from chunk_order and beat_index
        beat_index = int(beat_dict['beat_index'])
        beat_dict['id'] = f"chunk-{chunk_order}-{beat_index}"

        beat_dict.setdefault('location', '')
        beat_dict.setdefault('scene_timing', '')

        # Normalize characters: ensure each character is a dict with 'name' key
        raw_characters = beat_dict.get('characters', [])
        normalized_characters = []
        for c in raw_characters:
            if isinstance(c, str):
                normalized_characters.append({'name': c})
            elif isinstance(c, dict) and c.get('name'):
                normalized_characters.append(c)
        beat_dict['characters'] = normalized_characters

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
        """Extract narrative beats from a chunk using direct LLM call."""
        if self.llm is None:
            raise ValueError("LLM API Key 未配置。请设置 DEEPSEEK_API_KEY 环境变量。")

        debug("agent1", "[Chunk {}] Starting extraction with direct LLM", chunk.id)

        context_hint = "" if chunk.order == 0 else "You may consider previous context if available."

        # Get known characters for reference
        chars_hint = self.get_known_characters_context()

        try:
            user_message = f"""Analyze this text and extract narrative beats:

Text to analyze:
{chunk.text}

Chunk order: {chunk.order}
{chars_hint}

{context_hint}

IMPORTANT: Use EXACT character names from the known characters list above. Do NOT use "主人公" or "主角".

Output ONLY the JSON array in your response, no explanation."""

            response = await self.llm.ainvoke([
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=user_message)
            ])

            output = response.content if hasattr(response, 'content') and response.content else ""
            debug("agent1", "[Chunk {}] LLM output: {}", chunk.id, str(output)[:500])

            beats_list = self._parse_beats(output)

            if not beats_list and output:
                logger.warning(f"[Chunk {chunk.id}] Failed to parse beats from output: {output[:200]}")

        except Exception as e:
            debug("agent1", "[Chunk {}] LLM execution failed: {}", chunk.id, str(e))
            beats_list = []

        validated_beats = []
        invalid_count = 0
        for beat_dict in beats_list:
            validated = self._validate_beat(beat_dict, chunk.order)
            if validated:
                validated_beats.append(validated)
            else:
                invalid_count += 1

        debug("agent1", "[Chunk {}] Validated {} beats, {} invalid", chunk.id, len(validated_beats), invalid_count)
        return validated_beats

    def _parse_beats(self, content: str) -> list:
        """Parse beats from LLM output."""
        if not content:
            return []

        # Strip markdown code blocks
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and 'beats' in parsed:
                return parsed['beats']
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in content
        json_match = re.search(r'\[\s*\{[^}\]]*"beat_index"\s*:[^}\]]*\}', cleaned)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"Failed to parse beats from output: {content}")
        return []