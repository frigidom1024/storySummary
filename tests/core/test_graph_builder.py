import pytest
from src.core.graph_builder import GraphBuilder, ThreadState


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
async def test_graph_builder_defaults():
    builder = GraphBuilder()
    builder.llm = None
    nodes = [{"id": "n-0-0", "characters": [{"name": "陈屿"}]}]
    results = await builder.build(nodes, [], thread_enabled=True)
    assert results[0]["thread_id"] == "main"
