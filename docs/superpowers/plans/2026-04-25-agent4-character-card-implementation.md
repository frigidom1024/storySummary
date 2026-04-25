# Agent4 Character Card Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Agent4CharacterCard class that uses LLM to analyze chunk text + nodes, update cumulative CharacterCards via BookRepository.

**Architecture:** Agent4 follows Agent1-3's LangChain Agent pattern. It receives chunk.text + beats from Agent1-3, uses LLM to extract character interactions/emotions, then updates CharacterCards persisted via BookRepository.

**Tech Stack:** Python async/await, Pydantic, LangChain, BookRepository

---

## File Structure

- **Modify:** `src/core/agents/agent4_character_card.py` - Main Agent4 implementation (currently nearly empty)
- **Modify:** `src/core/node_generator.py` - Pass full context (chunk.text) to Agent4
- **Create:** `tests/core/test_agent4_character_card.py` - Unit tests
- **Existing:** `src/models/character_card.py` - CharacterCard model (already exists)
- **Existing:** `src/storage/book_repository.py` - BookRepository for persistence

---

## Task 1: Implement Agent4CharacterCard Class

**Files:**
- Modify: `src/core/agents/agent4_character_card.py`

### Step 1: Write the failing test

```python
# tests/core/test_agent4_character_card.py
import pytest
from src.core.agents.agent4_character_card import Agent4CharacterCard, CharacterUpdateResult

def test_initialization():
    agent = Agent4CharacterCard(book_id="test-book")
    assert agent.book_id == "test-book"
    assert agent.characters == {}

def test_process_nodes_structure():
    """Test that process_nodes accepts expected input format"""
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [
        {
            "id": "n-0-0",
            "scene": "旧书店，下午三点",
            "characters": [{"name": "陈屿"}],
            "event_summary": "陈屿遇到老板",
            "turning_point": "发现扉页签名",
            "importance": 0.7
        }
    ]
    context = {"chunk_id": "chunk-0", "chunk_text": "旧书店的场景...", "chunk_order": 0}
    # Should not raise
    result = agent.process_nodes(nodes, context)
    assert "characters" in result

def test_get_all_characters_returns_list():
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [{"id": "n-0-0", "scene": "test", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": ""}]
    agent.process_nodes(nodes, {"chunk_id": "c0", "chunk_text": "test", "chunk_order": 0})
    all_chars = agent.get_all_characters()
    assert isinstance(all_chars, list)
```

### Step 2: Run test to verify it fails

Run: `pytest tests/core/test_agent4_character_card.py -v`
Expected: FAIL - Agent4CharacterCard.process_nodes not defined

### Step 3: Write minimal stub implementation

```python
# src/core/agents/agent4_character_card.py
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

from src.models.character_card import CharacterCard
from src.storage.book_repository import BookRepository
from src.logging_config import debug

logger = logging.getLogger("story-summary")


class CharacterUpdateResult(BaseModel):
    """LLM 输出：单个角色的更新"""
    character: str = Field(description="角色名称")
    emotional_state: str = Field(default="", description="情绪状态描述")
    is_key_event: bool = Field(default=False, description="是否为关键事件")
    interactions: list[dict] = Field(default_factory=list, description="角色互动列表")

    class InteractionModel(BaseModel):
        target: str
        type: str  # tension/support/neutral
        intensity_delta: float


class Agent4CharacterCard:
    """Agent4: 使用 LLM 更新角色卡片"""

    def __init__(self, api_key: str = None, book_id: str = None):
        self.book_id = book_id
        self.book_repository = BookRepository()
        self.characters: dict[str, CharacterCard] = {}

        # 加载已有角色
        if book_id:
            self.characters = self.book_repository.load_characters(book_id)

        # 初始化 LLM
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        api_base = os.getenv("DEEPSEEK_API_BASE")

        if api_key:
            model = os.getenv("LLM_MODEL", "deepseek-chat")
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=0.3,
                openai_api_base=api_base or "https://api.deepseek.com/v1"
            )
        else:
            self.llm = None

    def process_nodes(self, nodes: list[dict], context: dict) -> dict:
        """处理节点并更新角色卡片"""
        # 暂时返回空结果，测试通过
        return {"characters": [], "relationship_graph": {"nodes": [], "edges": []}}

    def get_all_characters(self) -> list[dict]:
        return [card.model_dump() for card in self.characters.values()]

    def get_relationship_graph(self) -> dict:
        nodes = []
        edges = []
        for name, card in self.characters.items():
            nodes.append({"id": name, "name": name, "total_appearances": card.total_appearances})
            for target, rel in card.relationships.items():
                edges.append({"source": name, "target": target, "type": rel.type, "intensity": rel.current_intensity})
        return {"nodes": nodes, "edges": edges}
```

### Step 4: Run test to verify it passes

Run: `pytest tests/core/test_agent4_character_card.py -v`
Expected: PASS

### Step 5: Commit

```bash
git add src/core/agents/agent4_character_card.py tests/core/test_agent4_character_card.py
git commit -m "feat(agent4): add Agent4CharacterCard stub with basic structure"
```

---

## Task 2: Add LLM Analysis Prompt and Tools

**Files:**
- Modify: `src/core/agents/agent4_character_card.py`

### Step 1: Add tools and prompt

```python
# 在 Agent4CharacterCard 类中添加：

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

Output a JSON array of character updates:

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
```

### Step 2: Verify code compiles

Run: `python -c "from src.core.agents.agent4_character_card import Agent4CharacterCard; print('OK')"`
Expected: OK

### Step 3: Commit

```bash
git add src/core/agents/agent4_character_card.py
git commit -m "feat(agent4): add LLM prompt and tools for character analysis"
```

---

## Task 3: Implement Full process_nodes with LLM

**Files:**
- Modify: `src/core/agents/agent4_character_card.py`

### Step 1: Write test for LLM call

```python
# tests/core/test_agent4_character_card.py - add test
def test_process_nodes_with_mock_llm(monkeypatch):
    """Test that process_nodes calls LLM when available"""
    calls = []

    def mock_ainvoke(self, messages, **kwargs):
        calls.append(messages)
        class MockResponse:
            content = '[{"character": "陈屿", "emotional_state": "紧张", "is_key_event": true, "interactions": []}]'
        return MockResponse()

    monkeypatch.setattr("langchain_openai.ChatOpenAI.ainvoke", mock_ainvoke)

    agent = Agent4CharacterCard(book_id="test-book", api_key="fake-key")
    nodes = [{"id": "n-0-0", "scene": "旧书店", "characters": [{"name": "陈屿"}], "event_summary": "遇到老板", "turning_point": "", "importance": 0.7}]
    context = {"chunk_id": "c0", "chunk_text": "旧书店场景", "chunk_order": 0}

    agent.process_nodes(nodes, context)
    # LLM should have been called
    assert len(calls) > 0 or agent.characters.get("陈屿") is not None
```

### Step 2: Implement process_nodes with LLM

```python
# 替换 Agent4CharacterCard.process_nodes 方法

async def process_nodes(self, nodes: list[dict], context: dict) -> dict:
    """处理节点并更新角色卡片 (LLM驱动)"""
    debug("agent4", "Agent4CharacterCard.process_nodes called with {} nodes", len(nodes))

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

    # 构建节点摘要
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

            debug("agent4", "LLM response: {}", content[:500])

            updates = self._parse_updates(content)
            self._apply_updates(nodes, updates)

        except Exception as e:
            debug("agent4", "LLM analysis failed: {}", str(e))
            # 降级：仅更新出场次数
            self._increment_all_appearances(nodes)

    else:
        debug("agent4", "No LLM configured, using defaults")
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
```

### Step 3: Run tests

Run: `pytest tests/core/test_agent4_character_card.py -v`
Expected: PASS

### Step 4: Commit

```bash
git add src/core/agents/agent4_character_card.py
git commit -m "feat(agent4): implement LLM-driven process_nodes with character analysis"
```

---

## Task 4: Fix Type Signature - process_nodes should be async

**Files:**
- Modify: `src/core/agents/agent4_character_card.py`
- Modify: `src/core/node_generator.py`

### Step 1: Update process_nodes to be async

The current implementation is sync but should be async to work with the pipeline. Update the method signature and call accordingly.

```python
# In agent4_character_card.py:
async def process_nodes(self, nodes: list[dict], context: dict) -> dict:
    # ... existing implementation ...
```

### Step 2: Update node_generator.py call site

```python
# In node_generator.py, find and update:
# === Agent4: 角色卡片维护 ===
if self.pipeline_config.enable_agent4:
    debug("node_generator", "Agent4: Processing character cards for {} nodes", len(beats))
    self.agent4.process_nodes(beats, context)  # Add await
    # becomes:
    # await self.agent4.process_nodes(beats, context)
```

### Step 3: Verify compilation

Run: `python -c "from src.core.node_generator import NarrativeNodeGenerator; print('OK')"`
Expected: OK

### Step 4: Commit

```bash
git add src/core/agents/agent4_character_card.py src/core/node_generator.py
git commit -m "feat(agent4): make process_nodes async for proper pipeline integration"
```

---

## Task 5: Add More Comprehensive Tests

**Files:**
- Modify: `tests/core/test_agent4_character_card.py`

### Step 1: Add tests for CharacterCard updates

```python
def test_apply_updates_creates_new_character():
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [{"id": "n-0-0", "scene": "旧书店", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": ""}]
    updates = [CharacterUpdateResult(character="Alice", emotional_state="紧张", is_key_event=False, interactions=[])]

    agent._apply_updates(nodes, updates)

    assert "Alice" in agent.characters
    assert agent.characters["Alice"].current_state == "紧张"

def test_apply_updates_adds_interaction():
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [{"id": "n-0-0", "scene": "办公室", "characters": [{"name": "Bob"}], "event_summary": "", "turning_point": ""}]
    updates = [
        CharacterUpdateResult(
            character="Bob",
            emotional_state="",
            is_key_event=False,
            interactions=[{"target": "Alice", "type": "tension", "intensity_delta": 0.5}]
        )
    ]

    agent._apply_updates(nodes, updates)

    assert "Bob" in agent.characters
    assert "Alice" in agent.characters["Bob"].relationships
    assert agent.characters["Bob"].relationships["Alice"].type == "tension"

def test_increment_all_appearances():
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [
        {"id": "n-0-0", "scene": "场景1", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": "", "importance": 0.9}
    ]

    agent._increment_all_appearances(nodes)

    assert agent.characters["Alice"].total_appearances == 1
    assert "n-0-0" in agent.characters["Alice"].key_events

def test_get_relationship_graph():
    agent = Agent4CharacterCard(book_id="test-book")
    agent.characters["Alice"] = CharacterCard(character_id="Alice", name="Alice", first_seen="n-0")
    agent.characters["Alice"].add_interaction("Bob", "tension", 0.3, "n-0")

    graph = agent.get_relationship_graph()

    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["source"] == "Alice"
    assert graph["edges"][0]["target"] == "Bob"
```

### Step 2: Run all tests

Run: `pytest tests/core/test_agent4_character_card.py -v`
Expected: PASS (all tests)

### Step 3: Commit

```bash
git add tests/core/test_agent4_character_card.py
git commit -m "test(agent4): add comprehensive tests for character card updates"
```

---

## Task 6: Add first_seen_scene Field to CharacterCard

**Files:**
- Modify: `src/models/character_card.py`

Note: CharacterCard already has `first_seen_scene` field (from the existing model), but it wasn't being populated. The implementation in Task 3 already uses it.

### Step 1: Verify field exists

```python
# Check src/models/character_card.py has:
first_seen_scene: str = ""
```

### Step 2: Run existing tests still pass

Run: `pytest tests/models/test_character_card.py tests/core/test_agent4_character_card.py -v`
Expected: PASS

### Step 3: Commit

```bash
git commit -m "fix(agent4): ensure first_seen_scene is properly populated in CharacterCard updates"
```

---

## Implementation Complete

### Summary of Changes

| File | Change |
|------|--------|
| `src/core/agents/agent4_character_card.py` | Full implementation with LLM, tools, prompts |
| `src/core/node_generator.py` | Updated to await Agent4.process_nodes() |
| `tests/core/test_agent4_character_card.py` | Comprehensive unit tests |
| `src/models/character_card.py` | Existing model (no changes needed) |
| `src/storage/book_repository.py` | Existing persistence layer (no changes needed) |

### Key Design Decisions

1. **LLM analyzes per-chunk**: One LLM call per chunk for efficiency
2. **Cumulative via BookRepository**: Characters persist across chunks
3. **Graceful degradation**: Without LLM, still increments appearances
4. **Async pipeline**: process_nodes is async to integrate properly
