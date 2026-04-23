import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.story_graph import StoryGraph
from src.models.narrative_node import NarrativeNode, CharacterState


def make_node(node_id: str, thread_id: str = "main", time_label: str = "NOW",
              importance: float = 0.5, chars: list[str] = None,
              parent_chunk_id: str = "c-0", beat_index: int = 0,
              thread_prev: str = "") -> NarrativeNode:
    """Helper to create a test node with simplified model."""
    return NarrativeNode(
        id=node_id,
        parent_chunk_id=parent_chunk_id,
        beat_index=beat_index,
        thread_id=thread_id,
        thread_name=f"{thread_id}线",
        time_label=time_label,
        importance=importance,
        thread_prev_node_id=thread_prev,
        characters=[CharacterState(name=c) for c in (chars or [])],
        scene=f"场景-{node_id}",
        situation=f"情境-{node_id}",
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
    """Test get_thread returns nodes in story order via thread_prev_node_id links."""
    nodes = [
        make_node("n-0", thread_id="main", beat_index=0, thread_prev=""),
        make_node("n-1", thread_id="main", beat_index=1, thread_prev="n-0"),
        make_node("n-3", thread_id="main", beat_index=2, thread_prev="n-1"),
    ]
    sg = StoryGraph(nodes)
    thread_nodes = sg.get_thread("main")
    ids = [n.id for n in thread_nodes]
    assert ids == ["n-0", "n-1", "n-3"]


def test_get_timeline_order():
    """Test get_timeline_order sorts by time_label (PAST -> NOW -> FUTURE)."""
    nodes = [
        make_node("n-2", time_label="FUTURE"),
        make_node("n-0", time_label="PAST"),
        make_node("n-1", time_label="NOW"),
    ]
    sg = StoryGraph(nodes)
    ordered = sg.get_timeline_order()
    ids = [n.id for n in ordered]
    assert ids == ["n-0", "n-1", "n-2"]  # PAST → NOW → FUTURE


def test_get_convergence_points():
    """Test get_convergence_points returns main thread nodes with multiple characters."""
    nodes = [
        make_node("n-0", chars=["林夏"]),
        make_node("n-1", thread_id="main", chars=["林夏", "陈远"]),
        make_node("n-2", thread_id="main", chars=["林夏", "张博"]),
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
        make_node("n-1", thread_id="zhang", chars=["林夏"]),
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
        make_node("n-0", thread_id="main", beat_index=0),
        make_node("n-1", thread_id="main", beat_index=1, thread_prev="n-0"),
    ]
    sg = StoryGraph(nodes)
    assert sg.get_threads() == ["main"]
    assert len(sg.get_thread("main")) == 2


def test_get_text_order():
    """Test get_text_order returns nodes in forward order via parent_chunk_id and beat_index."""
    nodes = [
        NarrativeNode(id="n-0", parent_chunk_id="c-0", beat_index=0,
                      thread_id="main", time_label="NOW",
                      scene="s0", situation="s0"),
        NarrativeNode(id="n-1", parent_chunk_id="c-0", beat_index=1,
                      thread_id="main", time_label="NOW",
                      scene="s1", situation="s1"),
        NarrativeNode(id="n-2", parent_chunk_id="c-0", beat_index=2,
                      thread_id="main", time_label="NOW",
                      scene="s2", situation="s2"),
    ]
    sg = StoryGraph(nodes)
    ordered = sg.get_text_order()
    ids = [n.id for n in ordered]
    assert ids == ["n-0", "n-1", "n-2"]
