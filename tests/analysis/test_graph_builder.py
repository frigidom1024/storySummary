import pytest
from src.analysis.agents.agent2_thread_marker import Agent2ThreadMarker, ThreadState


def test_thread_state():
    state = ThreadState()
    state.add_thread("main", ["陈屿", "老板"])
    state.set_last_node("main", "n-0-0")
    assert "陈屿" in state.threads["main"]
    assert state.get_last_node("main") == "n-0-0"


def test_find_best_thread():
    state = ThreadState()
    state.add_thread("main", ["陈屿", "老板"])
    best, ratio = state.find_best_thread(["陈屿"])
    assert best == "main"
    assert ratio == 1.0


@pytest.mark.asyncio
async def test_agent2_mark_defaults():
    """Test Agent2 returns defaults when LLM is disabled"""
    agent = Agent2ThreadMarker()
    agent.llm = None
    nodes = [{"id": "n-0-0", "characters": [{"name": "陈屿"}]}]
    results = await agent.mark(nodes)
    assert results[0]["thread_id"] == "main"
    assert results[0]["thread_prev_node_id"] == ""
