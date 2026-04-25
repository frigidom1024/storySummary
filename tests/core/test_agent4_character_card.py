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