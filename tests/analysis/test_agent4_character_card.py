import pytest
import asyncio
from src.analysis.agents.agent4_character_card import Agent4CharacterCard, CharacterUpdateResult
from src.models.character_card import CharacterCard

def test_initialization():
    agent = Agent4CharacterCard(book_id="test-book")
    assert agent.book_id == "test-book"
    assert agent.characters == {}

@pytest.mark.asyncio
async def test_process_nodes_structure():
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
    result = await agent.process_nodes(nodes, context)
    assert "characters" in result

@pytest.mark.asyncio
async def test_get_all_characters_returns_list():
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [{"id": "n-0-0", "scene": "test", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": ""}]
    await agent.process_nodes(nodes, {"chunk_id": "c0", "chunk_text": "test", "chunk_order": 0})
    all_chars = agent.get_all_characters()
    assert isinstance(all_chars, list)


def test_apply_updates_creates_new_character():
    """Test that _apply_updates creates a new character card"""
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [{"id": "n-0-0", "scene": "旧书店", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": ""}]
    updates = [CharacterUpdateResult(character="Alice", emotional_state="紧张", is_key_event=False, interactions=[])]

    agent._apply_updates(nodes, updates)

    assert "Alice" in agent.characters
    assert agent.characters["Alice"].current_state == "紧张"


def test_apply_updates_adds_interaction():
    """Test that _apply_updates adds a relationship"""
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
    """Test that _increment_all_appearances works as fallback"""
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [
        {"id": "n-0-0", "scene": "场景1", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": "", "importance": 0.9}
    ]

    agent._increment_all_appearances(nodes)

    assert agent.characters["Alice"].total_appearances == 1
    assert "n-0-0" in agent.characters["Alice"].key_events


def test_get_relationship_graph():
    """Test that get_relationship_graph returns proper structure"""
    agent = Agent4CharacterCard(book_id="test-book")
    agent.characters["Alice"] = CharacterCard(character_id="Alice", name="Alice", first_seen="n-0")
    agent.characters["Alice"].add_interaction("Bob", "tension", 0.3, "n-0")

    graph = agent.get_relationship_graph()

    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["source"] == "Alice"
    assert graph["edges"][0]["target"] == "Bob"


def test_find_node_for_character():
    """Test _find_node_for_character helper"""
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [
        {"id": "n-0-0", "scene": "scene1", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": ""},
        {"id": "n-0-1", "scene": "scene2", "characters": [{"name": "Bob"}], "event_summary": "", "turning_point": ""}
    ]

    result = agent._find_node_for_character(nodes, "Bob")
    assert result["id"] == "n-0-1"


def test_find_node_for_character_not_found():
    """Test _find_node_for_character returns None when not found"""
    agent = Agent4CharacterCard(book_id="test-book")
    nodes = [{"id": "n-0-0", "scene": "scene1", "characters": [{"name": "Alice"}], "event_summary": "", "turning_point": ""}]

    result = agent._find_node_for_character(nodes, "Charlie")
    assert result is None