"""Tool implementations — SQLite queries via existing storage layer."""

import tempfile
import os
from src.storage.database import Database


def get_previous_chunk_nodes_impl(book_id: str, db_path: str | None = None, **kwargs) -> list[dict]:
    """Get all nodes from the previous chunk (T1 implementation).

    Queries the database for the highest-order chunk less than the current one,
    then returns all nodes in that chunk.
    """
    if db_path is None:
        db_path = os.path.join(tempfile.gettempdir(), "story_summary_tool_test.db")
    db = Database(db_path)
    chunks = db.get_chunks_for_book(book_id)
    if not chunks:
        return []

    last_chunk = max(chunks, key=lambda c: c.get("order", 0))
    last_chunk_id = last_chunk.get("id", "")
    if not last_chunk_id:
        return []

    nodes = db.get_nodes_for_book(book_id)
    prev_nodes = [
        {
            "id": n.id,
            "timeline_anchor": n.timeline_anchor,
            "thread_id": n.thread_id,
            "characters": [c.name for c in n.characters],
            "narrative_role": n.narrative_role,
        }
        for n in nodes
        if n.parent_chunk_id == last_chunk_id
    ]
    return prev_nodes


def get_thread_last_node_impl(book_id: str, thread_id: str, db_path: str | None = None, **kwargs) -> dict | None:
    """Get the last node in a thread chain (T2 implementation).

    Finds the node in the given thread that has no incoming thread_next_node_id.
    """
    if db_path is None:
        db_path = os.path.join(tempfile.gettempdir(), "story_summary_tool_test.db")
    db = Database(db_path)
    nodes = db.get_nodes_for_book(book_id)

    thread_nodes = [n for n in nodes if n.thread_id == thread_id]
    if not thread_nodes:
        return None

    tails = set()
    all_next_ids = {n.thread_next_node_id for n in thread_nodes if n.thread_next_node_id}

    for n in thread_nodes:
        if n.id not in all_next_ids:
            tails.add(n.id)

    if not tails:
        return None

    tail_node = max(thread_nodes, key=lambda n: n.beat_index)
    return {
        "id": tail_node.id,
        "timeline_anchor": tail_node.timeline_anchor,
        "beat_index": tail_node.beat_index,
    }


def search_nodes_impl(book_id: str, keyword: str, db_path: str | None = None, **kwargs) -> list[dict]:
    """Search nodes by character name (T3 implementation)."""
    if db_path is None:
        db_path = os.path.join(tempfile.gettempdir(), "story_summary_tool_test.db")
    db = Database(db_path)
    nodes = db.get_nodes_for_book(book_id)

    results = []
    for n in nodes:
        char_names = [c.name for c in n.characters]
        if any(keyword in name for name in char_names):
            results.append({
                "id": n.id,
                "thread_id": n.thread_id,
                "scene": n.scene[:50] if n.scene else "",
                "characters": char_names,
            })
    return results


TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
}
