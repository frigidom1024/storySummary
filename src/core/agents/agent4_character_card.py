"""Agent4: Character Card Manager - 角色卡片维护"""
import logging
import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.character_card import CharacterCard
from src.core.agents.tools import AgentTools
from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


def create_character_llm(api_key: str | None = None) -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    kwargs = {"api_key": api_key, "model": model, "temperature": 0.3}
    if api_base:
        kwargs["openai_api_base"] = api_base
    return ChatOpenAI(**kwargs)


class Agent4CharacterCard:
    """Agent4: 维护角色卡片，分析角色关系和状态变化

    职责：
    - 追踪角色登场次数和关键事件
    - 维护角色关系图谱
    - 跟踪角色情绪状态变化
    - 生成角色描述和人物小传
    """

    def __init__(self, api_key: str = None, book_id: str = None):
        self.characters: dict[str, CharacterCard] = {}
        self.llm = create_character_llm(api_key=api_key) if api_key or os.getenv("DEEPSEEK_API_KEY") else None
        self.agent_tools = AgentTools(book_id=book_id)

    def set_search_fn(self, fn):
        self.agent_tools.set_search_fn(fn)

    def set_get_thread_last_fn(self, fn):
        self.agent_tools.set_get_thread_last_fn(fn)

    def get_tools(self):
        return self.agent_tools.get_tools()

    def process_nodes(self, nodes: list[dict], context: dict | None = None) -> None:
        """处理一批节点，更新角色卡片

        Args:
            nodes: 叙事节点列表
            context: 上下文信息，包含 chunk_text 等
        """
        debug_log("agent4", "Agent4 process_nodes called with {} nodes, current char count={}, context_keys={}",
                  len(nodes), len(self.characters), list(context.keys()) if context else [])

        for node in nodes:
            self._process_node(node)

        debug_log("agent4", "Agent4: After processing {} characters tracked", len(self.characters))

    def _process_node(self, node: dict) -> None:
        """处理单个节点，提取角色信息"""
        characters = node.get("characters", [])
        interactions = node.get("interactions", [])
        node_id = node.get("id", "")
        importance = float(node.get("importance", 0.5))
        scene = node.get("scene", "")

        debug_log("agent4", "  Processing node_id={} chars={} interactions={} importance={}",
                  node_id, [c.get("name") for c in characters], len(interactions), importance)

        names = [c.get("name", "") for c in characters if c.get("name")]

        # 创建或更新角色卡片
        for char in characters:
            name = char.get("name", "")
            if not name:
                continue

            if name not in self.characters:
                self.characters[name] = CharacterCard(
                    character_id=name,
                    name=name,
                    first_seen=node_id,
                    current_state=char.get("state_before", ""),
                )
                debug_log("agent4", "    New character: {} first_seen={}", name, node_id)

            card = self.characters[name]
            card.increment_appearance()

            # 更新情绪状态
            if char.get("state_before"):
                card.update_emotional_state(char["state_before"], node_id)

            # 记录重要事件
            if importance >= 0.8:
                card.add_key_event(node_id)
                debug_log("agent4", "    Key event added for {} at {}", name, node_id)

            # 更新首次登场的场景描述
            if card.total_appearances == 1 and scene:
                card.first_seen_scene = scene

        # 处理角色互动
        source_char = names[0] if names else ""
        for interaction in interactions:
            debug_log("agent4", "    Interaction: {} -> {} type={} delta={}",
                      source_char, interaction.get("target"), interaction.get("type"), interaction.get("intensity_delta"))

            if source_char and source_char in self.characters:
                self.characters[source_char].add_interaction(
                    target=interaction.get("target", ""),
                    interaction_type=interaction.get("type", "neutral"),
                    intensity_delta=float(interaction.get("intensity_delta", 0.0)),
                    node_id=node_id,
                )

    async def analyze_character(self, character_name: str) -> dict:
        """使用 LLM 分析角色，生成角色描述"""
        if not self.llm:
            return {}

        card = self.characters.get(character_name)
        if not card:
            return {}

        debug_log("agent4", "Analyzing character: {}", character_name)

        # 构建角色上下文
        context = {
            "name": character_name,
            "total_appearances": card.total_appearances,
            "first_seen": card.first_seen,
            "current_state": card.current_state,
            "relationships": [
                {"target": k, "type": v.type, "intensity": v.current_intensity}
                for k, v in card.relationships.items()
            ],
            "key_events": card.key_events[-5:] if card.key_events else [],
            "emotional_history": card.emotional_history[-10:] if card.emotional_history else [],
        }

        prompt = f"""分析以下角色，生成角色描述：

角色信息：
{context}

请生成：
1. 角色性格特点
2. 在故事中的作用
3. 与其他角色的关系概述
4. 情感/心理状态变化轨迹

请用中文回答，格式为JSON。
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a character analyst. Output ONLY JSON."),
                HumanMessage(content=prompt)
            ])
            content = response.content if getattr(response, "content", None) else "{}"
            import json
            result = json.loads(content)
            debug_log("agent4", "Character analysis complete for {}", character_name)
            return result
        except Exception as e:
            logger.warning("Failed to analyze character %s: %s", character_name, str(e))
            return {}

    def get_character(self, name: str) -> Optional[CharacterCard]:
        """获取角色卡片"""
        return self.characters.get(name)

    def get_all_characters(self) -> dict[str, CharacterCard]:
        """获取所有角色卡片"""
        return self.characters

    def get_relationship_graph(self) -> dict:
        """获取角色关系图，用于可视化"""
        nodes = []
        edges = []

        for char_name, card in self.characters.items():
            nodes.append({
                "id": char_name,
                "name": char_name,
                "total_appearances": card.total_appearances,
                "current_state": card.current_state,
            })

            for target, rel in card.relationships.items():
                edges.append({
                    "source": char_name,
                    "target": target,
                    "type": rel.type,
                    "intensity": rel.current_intensity,
                })

        return {"nodes": nodes, "edges": edges}

    def get_characters_by_thread(self, thread_id: str, nodes: list[dict]) -> list[str]:
        """获取指定叙事线中的角色列表"""
        thread_chars = set()
        for node in nodes:
            if node.get("thread_id") == thread_id:
                for char in node.get("characters", []):
                    if char.get("name"):
                        thread_chars.add(char["name"])
        return list(thread_chars)
