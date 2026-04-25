"""Agent4: Character Card Agent - 角色卡片管理"""
import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from src.models.character_card import CharacterCard, Relationship, EmotionalSnapshot
from src.storage.book_repository import BookRepository

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


class Agent4CharacterCard:
    """Agent4: 管理角色卡片的创建和更新"""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.repository = BookRepository()
        self.characters = {}

        if book_id:
            self.characters = self.repository.load_characters(book_id)

    def process_nodes(self, nodes: list[dict], context: dict) -> dict:
        """处理节点并更新角色卡片

        Args:
            nodes: 叙事节点列表
            context: 包含 chunk_id, chunk_text, chunk_order 的上下文

        Returns:
            包含 characters 和 relationship_graph 的字典
        """
        # Stub implementation - returns empty structure
        return {
            "characters": [],
            "relationship_graph": {
                "nodes": [],
                "edges": []
            }
        }

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
