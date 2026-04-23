import pytest
from src.core.agents.agent2_thread_marker import Agent2ThreadMarker


def test_agent2_thread_marker_init():
    """Test Agent2 can be initialized"""
    agent = Agent2ThreadMarker()
    assert agent is not None
    assert agent.thread_state is not None


def test_agent2_thread_state():
    """Test ThreadState functionality"""
    agent = Agent2ThreadMarker()
    state = agent.thread_state

    # Add thread
    state.add_thread("main", ["陈屿", "沈昭"])
    assert "main" in state.threads
    assert "陈屿" in state.threads["main"]

    # Set last node
    state.set_last_node("main", "n-0-0")
    assert state.get_last_node("main") == "n-0-0"


def test_find_best_thread():
    """Test thread assignment based on character overlap"""
    agent = Agent2ThreadMarker()
    state = agent.thread_state

    state.add_thread("main", ["陈屿", "沈昭"])

    # Exact match
    best, ratio = state.find_best_thread(["陈屿"])
    assert best == "main"
    assert ratio == 1.0

    # Partial match
    best, ratio = state.find_best_thread(["陈屿", "新角色"])
    assert best == "main"
    assert ratio == 0.5


def test_build_with_defaults():
    """Test default values when LLM is disabled"""
    agent = Agent2ThreadMarker()
    nodes = [{"id": "n-0-0", "scene": "test"}]
    result = agent._build_with_defaults(nodes)

    assert len(result) == 1
    assert result[0]["thread_id"] == "main"
    assert result[0]["thread_prev_node_id"] == ""
