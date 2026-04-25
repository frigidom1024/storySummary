"""Agent4: Character Card Agent - 角色卡片管理"""
import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.models.character_card import CharacterCard, Relationship, EmotionalSnapshot
from src.storage.book_repository import BookRepository
from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


class CharacterUpdateResult(BaseModel):
    """角色更新结果"""
    character: str = Field(description="Character name")
    emotional_state: str = Field(default="", description="Current emotional state")
    is_key_event: bool = Field(default=False, description="Whether this is a key event")
    interactions: list[dict] = Field(default_factory=list, description="List of interactions")


def create_character_tools(book_id: str):
    """创建 Agent4 工具"""
    from src.core.tools.tool_executor import get_previous_chunk_nodes_impl

    @tool
    def get_previous_chunk_nodes() -> str:
        """Return all nodes from the latest processed chunk for character context.

        Use this to understand what characters have appeared and their recent states.

        Returns:
            JSON array of recent nodes with character information.
        """
        result = get_previous_chunk_nodes_impl(book_id=book_id)
        return json.dumps(result if result else [], ensure_ascii=False)

    @tool
    def output_character_updates(updates: str) -> str:
        """Output the final character updates JSON. Use this when analysis is complete."""
        return updates

    return [get_previous_chunk_nodes, output_character_updates]


def create_character_prompt() -> str:
    return """You are a character relationship and emotion analyst. Your task is to analyze narrative nodes and update character cards.

For each character mentioned in the nodes, analyze:
1. **Emotional state**: What is the character's current emotional state based on the scene?
2. **Interactions**: Character interactions (target, type: tension/support/neutral, intensity_delta 0.0-1.0)
3. **Key events**: Is this scene significant for this character?

## Input Format

You will receive:
- **nodes**: List of narrative beats with scene, event_summary, turning_point, characters
- **existing_characters**: Current character card states (for context)

## Interaction Types
- **tension**: Conflict, argument, competition, distrust
- **support**: Cooperation, help, trust, affection
- **neutral**: No significant relationship change

## Intensity Scale
- 0.0-0.3: Minor interaction
- 0.4-0.6: Moderate interaction
- 0.7-1.0: Major/significant interaction

## Output Format

Output a JSON array of character updates (for ALL characters in ALL nodes):

```json
[
  {
    "character": "CharacterName",
    "emotional_state": "紧张/平静/愤怒/微妙...",
    "is_key_event": true,
    "interactions": [
      {"target": "OtherCharacter", "type": "tension", "intensity_delta": 0.3}
    ]
  }
]
```

Analyze these nodes and output character updates:"""


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return ChatOpenAI(**llm_kwargs)


class Agent4CharacterCard:
    """Agent4: 管理角色卡片的创建和更新"""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.book_repository = BookRepository()
        self.characters = {}

        api_base = os.getenv("DEEPSEEK_API_BASE")
        if self.api_key:
            self.llm = create_llm(api_key=self.api_key, temperature=0.3, api_base=api_base)
        else:
            self.llm = None

        if book_id:
            self.characters = self.book_repository.load_characters(book_id)

    async def process_nodes(self, nodes: list[dict], context: dict) -> dict:
        """处理节点并更新角色卡片 (LLM驱动) - 批量处理所有nodes"""
        debug_log("agent4", "Agent4CharacterCard.process_nodes called with {} nodes", len(nodes))

        if not nodes:
            return {"characters": self.get_all_characters(), "relationship_graph": self.get_relationship_graph()}

        # 构建已有角色上下文
        existing_chars_context = {}
        for name, card in self.characters.items():
            existing_chars_context[name] = {
                "total_appearances": card.total_appearances,
                "current_state": card.current_state,
                "relationships": {t: {"type": r.type, "intensity": r.current_intensity}
                                for t, r in card.relationships.items()}
            }

        # 构建节点摘要 - ALL nodes at once
        nodes_summary = []
        for node in nodes:
            nodes_summary.append({
                "id": node.get("id", ""),
                "scene": node.get("scene", ""),
                "event_summary": node.get("event_summary", ""),
                "turning_point": node.get("turning_point", ""),
                "characters": [c.get("name", "") for c in node.get("characters", [])],
                "importance": node.get("importance", 0.5)
            })

        # 如果有 LLM，进行分析
        if self.llm is not None:
            try:
                prompt = create_character_prompt()
                messages = [
                    SystemMessage(content=prompt),
                    HumanMessage(content=f"""Nodes to analyze:
{json.dumps(nodes_summary, ensure_ascii=False)}

Existing character states (for context):
{json.dumps(existing_chars_context, ensure_ascii=False)}

Current chunk text (for additional context):
{context.get("chunk_text", "")[:1000]}""")
                ]

                response = await self.llm.ainvoke(messages)
                content = response.content if hasattr(response, 'content') and response.content else "[]"

                debug_log("agent4", "LLM response: {}", content[:500])

                updates = self._parse_updates(content)
                self._apply_updates(nodes, updates)

            except Exception as e:
                debug_log("agent4", "LLM analysis failed: {}", str(e))
                self._increment_all_appearances(nodes)
        else:
            debug_log("agent4", "No LLM configured, using defaults")
            self._increment_all_appearances(nodes)

        # 保存到 BookRepository
        if self.book_id:
            self.book_repository.save_characters(self.book_id, self.characters)

        return {
            "characters": self.get_all_characters(),
            "relationship_graph": self.get_relationship_graph()
        }


    def _parse_updates(self, content: str) -> list[CharacterUpdateResult]:
        """解析 LLM 输出"""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return [CharacterUpdateResult(**item) for item in parsed if item.get("character")]
        except (json.JSONDecodeError, Exception):
            pass
        return []


    def _apply_updates(self, nodes: list[dict], updates: list[CharacterUpdateResult]) -> None:
        """应用 LLM 输出的更新到角色卡片"""
        for update in updates:
            char_name = update.character
            if not char_name:
                continue

            # 获取或创建卡片
            if char_name not in self.characters:
                first_node = self._find_node_for_character(nodes, char_name)
                self.characters[char_name] = CharacterCard(
                    character_id=char_name,
                    name=char_name,
                    first_seen=first_node.get("id", "") if first_node else "",
                    first_seen_scene=first_node.get("scene", "")[:200] if first_node else ""
                )

            card = self.characters[char_name]

            # 更新情绪
            if update.emotional_state:
                node_id = self._find_node_id_for_character(nodes, char_name)
                card.update_emotional_state(update.emotional_state, node_id or "")

            # 更新出场次数
            card.increment_appearance()

            # 处理互动
            for interaction in update.interactions:
                if interaction.get("target"):
                    card.add_interaction(
                        target=interaction["target"],
                        interaction_type=interaction.get("type", "neutral"),
                        intensity_delta=interaction.get("intensity_delta", 0.0),
                        node_id=self._find_node_id_for_character(nodes, char_name) or ""
                    )

            # 标记关键事件
            if update.is_key_event:
                node_id = self._find_node_id_for_character(nodes, char_name)
                if node_id:
                    card.add_key_event(node_id)


    def _find_node_for_character(self, nodes: list[dict], char_name: str) -> Optional[dict]:
        """查找包含该角色的第一个节点"""
        for node in nodes:
            for c in node.get("characters", []):
                if c.get("name") == char_name:
                    return node
        return None


    def _find_node_id_for_character(self, nodes: list[dict], char_name: str) -> Optional[str]:
        """查找包含该角色的节点 ID"""
        node = self._find_node_for_character(nodes, char_name)
        return node.get("id") if node else None


    def _increment_all_appearances(self, nodes: list[dict]) -> None:
        """降级处理：仅为所有角色增加出场次数"""
        for node in nodes:
            node_id = node.get("id", "")
            for c in node.get("characters", []):
                name = c.get("name", "")
                if not name:
                    continue
                if name not in self.characters:
                    self.characters[name] = CharacterCard(
                        character_id=name,
                        name=name,
                        first_seen=node_id,
                        first_seen_scene=node.get("scene", "")[:200]
                    )
                self.characters[name].increment_appearance()
                # 高 importance 标记为关键事件
                if node.get("importance", 0) >= 0.8:
                    self.characters[name].add_key_event(node_id)

    def get_all_characters(self) -> list[dict]:
        """获取所有角色卡片列表

        Returns:
            角色卡片字典列表
        """
        return [card.model_dump() for card in self.characters.values()]

    def get_relationship_graph(self) -> dict:
        """获取关系图数据用于可视化

        Returns:
            包含 nodes 和 edges 的关系图字典
        """
        return {
            "nodes": [],
            "edges": []
        }
