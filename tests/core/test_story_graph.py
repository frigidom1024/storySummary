import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.story_graph import StoryGraph
from src.models.narrative_node import NarrativeNode, CharacterState


def make_node(node_id: str, thread_id: str = "main", timeline_order: int = 0,
              prev: str = "", next_n: str = "",
              is_conv: bool = False, chars: list[str] = None) -> NarrativeNode:
    """Helper to create a test node."""
    return NarrativeNode(
        id=node_id,
        thread_id=thread_id,
        thread_name=f"{thread_id}线",
        timeline_order=timeline_order,
        thread_prev_node_id=prev,
        thread_next_node_id=next_n,
        is_convergence=is_conv,
        characters=[CharacterState(name=c) for c in (chars or [])],
        scene=f"场景-{node_id}",
        situation=f"情境-{node_id}",
        narrative_role="rising"
    )


def test_get_threads():
    """Test get_threads returns all thread IDs."""
    nodes = [
        make_node("n-0", thread_id="main"),
        make_node("n-1", thread_id="zhang"),
        make_node("n-2", thread_id="chenwei"),
    ]
    sg = StoryGraph(nodes)
    threads = sg.get_threads()
    assert set(threads) == {"main", "zhang", "chenwei"}


def test_get_thread_main():
    """Test get_thread returns nodes in story order."""
    # n-0 → n-3 (main thread)
    # n-1 → n-4 (zhang thread)
    nodes = [
        make_node("n-0", thread_id="main", timeline_order=0),
        make_node("n-1", thread_id="main", timeline_order=1, prev="n-0"),
        make_node("n-3", thread_id="main", timeline_order=2, prev="n-1"),
    ]
    sg = StoryGraph(nodes)
    thread_nodes = sg.get_thread("main")
    ids = [n.id for n in thread_nodes]
    assert ids == ["n-0", "n-1", "n-3"]


def test_get_timeline_order():
    """Test get_timeline_order sorts by timeline_order ASC."""
    nodes = [
        make_node("n-2", timeline_order=5),
        make_node("n-0", timeline_order=-10),
        make_node("n-1", timeline_order=0),
    ]
    sg = StoryGraph(nodes)
    ordered = sg.get_timeline_order()
    ids = [n.id for n in ordered]
    assert ids == ["n-0", "n-1", "n-2"]  # -10 → 0 → 5


def test_get_convergence_points():
    """Test get_convergence_points returns is_convergence nodes."""
    nodes = [
        make_node("n-0", is_conv=False),
        make_node("n-1", is_conv=True),
        make_node("n-2", is_conv=True),
    ]
    sg = StoryGraph(nodes)
    conv = sg.get_convergence_points()
    assert len(conv) == 2


def test_get_nodes_for_character():
    """Test get_nodes_for_character."""
    nodes = [
        make_node("n-0", chars=["林夏"]),
        make_node("n-1", chars=["林夏", "陈远"]),
        make_node("n-2", chars=["张博"]),
    ]
    sg = StoryGraph(nodes)
    linxia_nodes = sg.get_nodes_for_character("林夏")
    assert len(linxia_nodes) == 2


def test_get_character_threads():
    """Test get_character_threads returns which threads a character is on."""
    nodes = [
        make_node("n-0", thread_id="main", chars=["林夏"]),
        make_node("n-1", thread_id="zhang", chars=["林夏"]),  # 林夏 also appears on zhang thread
    ]
    sg = StoryGraph(nodes)
    threads = sg.get_character_threads("林夏")
    assert set(threads) == {"main", "zhang"}


def test_get_node_by_id():
    """Test get_node_by_id returns correct node."""
    nodes = [make_node("n-99")]
    sg = StoryGraph(nodes)
    n = sg.get_node_by_id("n-99")
    assert n is not None
    assert n.id == "n-99"
    assert sg.get_node_by_id("nonexistent") is None


def test_single_thread_default():
    """Single thread story with default thread_id=main."""
    nodes = [
        make_node("n-0", thread_id="main", timeline_order=0),
        make_node("n-1", thread_id="main", timeline_order=1, prev="n-0"),
    ]
    sg = StoryGraph(nodes)
    assert sg.get_threads() == ["main"]
    assert len(sg.get_thread("main")) == 2


def test_get_text_order():
    """Test get_text_order returns nodes in forward text order via prev_node_id chain."""
    # Chain: n-0 -> n-1 -> n-2 (n-2.prev=n-1, n-1.prev=n-0, n-0.prev=None)
    nodes = [
        NarrativeNode(id="n-0", thread_id="main", timeline_order=0,
                       prev_node_id="", beat_index=0,
                       thread_prev_node_id="", narrative_role="opening",
                       situation="s0"),
        NarrativeNode(id="n-1", thread_id="main", timeline_order=1,
                       prev_node_id="n-0", beat_index=1,
                       thread_prev_node_id="n-0", narrative_role="rising",
                       situation="s1"),
        NarrativeNode(id="n-2", thread_id="main", timeline_order=2,
                       prev_node_id="n-1", beat_index=2,
                       thread_prev_node_id="n-1", narrative_role="climax",
                       situation="s2"),
    ]
    sg = StoryGraph(nodes)
    ordered = sg.get_text_order()
    ids = [n.id for n in ordered]
    # Should be forward text order: n-0, n-1, n-2
    assert ids == ["n-0", "n-1", "n-2"]
