"""Agent4: Character Card Manager - 角色卡片维护"""
import json
import logging
import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.models.character_card import CharacterCard
from src.logging_config import debug as debug_log

logger = logging.getLogger("story-summary")


def create_llm(api_key: str = None, model: str = None, api_base: str = None, **kwargs) -> ChatOpenAI:
    """Create LLM client."""
    model = model or os.getenv("LLM_MODEL", "deepseek-chat")
    llm_kwargs = {"api_key": api_key, "model": model, **kwargs}
    if api_base:
        llm_kwargs["openai_api_base"] = api_base
    elif "deepseek" in (model or "").lower():
        llm_kwargs["openai_api_base"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
    return ChatOpenAI(**llm_kwargs)


def create_character_tools(book_id: str):
    """Create tools for character card agent."""
    from src.core.tools.tool_executor import search_nodes_impl

    @tool
    def search_character_events(character_name: str) -> str:
        """Search for all events related to a character."""
        result = search_nodes_impl(book_id=book_id, keyword=character_name)
        return json.dumps(result, ensure_ascii=False)

    @tool
    def output_character_analysis(analysis: str) -> str:
        """Output the final character analysis JSON. Use this when you have completed the analysis."""
        return analysis

    return [search_character_events, output_character_analysis]


class Agent4CharacterCard:
    """Agent4: 使用LangChain Agent维护角色卡片，分析角色关系和状态变化"""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.characters: dict[str, CharacterCard] = {}
        self.book_id = book_id
        
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")
        
        if api_key:
            self.llm = create_llm(api_key=api_key, temperature=0.3, api_base=api_base)
        else:
            self.llm = None

    def _create_agent(self):
        """Create a LangChain agent for character analysis."""
        tools = create_character_tools(self.book_id) if self.book_id else []
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are a character analyst. Your task is to analyze characters and generate character descriptions.

For each character, analyze:
1. Character personality traits
2. Role in the story
3. Relationship with other characters
4. Emotional/psychological state change trajectory

Output format: JSON with character analysis"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            HumanMessage(content="""Analyze this character:

Character info:
{character_info}

Recent events (for context):
{recent_events}

Output your final analysis using the output_character_analysis tool."""),
        ])

        agent = create_react_agent(self.llm, tools, prompt=prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=5)

    def process_nodes(self, nodes: list[dict], context: dict | None = None) -> None:
        """处理一批节点，更新角色卡片"""
        debug_log("agent4", "Agent4 process_nodes called with {} nodes, current char count={}",
                  len(nodes), len(self.characters))

        for node in nodes:
            self._process_node(node)

        debug_log("agent4", "Agent4: After processing {} characters tracked", len(self.characters))

    def _process_node(self, node: dict) -> None:
        """处理单个节点，提取角色信息"""
        characters = node.get("characters", [])
        node_id = node.get("id", "")
        importance = float(node.get("importance", 0.5))
        scene = node.get("scene", "")

        debug_log("agent4", "  Processing node_id={} chars={} importance={}",
                  node_id, [c.get("name") for c in characters], importance)

        names = [c.get("name", "") for c in characters if c.get("name")]

        for char in characters:
            name = char.get("name", "")
            if not name:
                continue

            if name not in self.characters:
                self.characters[name] = CharacterCard(
                    character_id=name,
                    name=name,
                    first_seen=node_id,
                    current_state="",
                )
                debug_log("agent4", "    New character: {} first_seen={}", name, node_id)

            card = self.characters[name]
            card.increment_appearance()

            # 记录重要事件
            if importance >= 0.8:
                card.add_key_event(node_id)
                debug_log("agent4", "    Key event added for {} at {}", name, node_id)

            # 更新首次登场的场景描述
            if card.total_appearances == 1 and scene:
                card.first_seen_scene = scene

    async def analyze_character(self, character_name: str) -> dict:
        """使用 LangChain Agent 分析角色，生成角色描述"""
        if not self.llm:
            return {}

        card = self.characters.get(character_name)
        if not card:
            return {}

        debug_log("agent4", "Analyzing character: {}", character_name)

        # 构建角色上下文
        character_info = {
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

        try:
            agent_executor = self._create_agent()
            
            result = await agent_executor.ainvoke({
                "character_info": json.dumps(character_info, ensure_ascii=False),
                "recent_events": json.dumps(card.key_events[-5:] if card.key_events else [], ensure_ascii=False)
            })

            output = result.get("output", "{}")
            debug_log("agent4", "Agent output: {}", output[:500])

            analysis = json.loads(output) if output else {}
            debug_log("agent4", "Character analysis complete for {}", character_name)
            return analysis
            
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
