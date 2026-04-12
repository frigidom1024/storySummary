"""Tool implementations — read from JSON files."""

import os
from src.storage.json_storage import JsonStorage

json_storage = JsonStorage()


def get_previous_chunk_nodes_impl(book_id: str, **kwargs) -> list[dict]:
    """Get all nodes from the previous chunk (T1 implementation)."""
    chunks_file = f"data/books/{book_id}/chunks.json"
    nodes_file = f"data/books/{book_id}/nodes.json"

    try:
        chunks = json_storage.read(chunks_file) or []
    except Exception:
        return []

    if not chunks:
        return []

    last_chunk = max(chunks, key=lambda c: c.get("order", 0))
    last_chunk_id = last_chunk.get("id", "")
    if not last_chunk_id:
        return []

    try:
        nodes_data = json_storage.read(nodes_file) or []
    except Exception:
        return []

    # Handle both list format and dict format
    if isinstance(nodes_data, dict):
        nodes_list = nodes_data.get("nodes", [])
    else:
        nodes_list = nodes_data

    prev_nodes = [
        {
            "id": n.get("id", ""),
            "timeline_anchor": n.get("timeline_anchor", ""),
            "thread_id": n.get("thread_id", ""),
            "characters": [c.get("name", "") for c in n.get("characters", []) if c.get("name")],
            "narrative_role": n.get("narrative_role", ""),
        }
        for n in nodes_list
        if n.get("parent_chunk_id") == last_chunk_id
    ]
    return prev_nodes


def get_thread_last_node_impl(book_id: str, thread_id: str, **kwargs) -> dict | None:
    """Get the last node in a thread chain (T2 implementation)."""
    nodes_file = f"data/books/{book_id}/nodes.json"

    try:
        nodes_data = json_storage.read(nodes_file) or []
    except Exception:
        return None

    # Handle both list format and dict format
    if isinstance(nodes_data, dict):
        nodes_list = nodes_data.get("nodes", [])
    else:
        nodes_list = nodes_data

    thread_nodes = [n for n in nodes_list if n.get("thread_id") == thread_id]
    if not thread_nodes:
        return None

    tails = set()
    all_next_ids = {n.get("thread_next_node_id") for n in thread_nodes if n.get("thread_next_node_id")}

    for n in thread_nodes:
        if n.get("id") not in all_next_ids:
            tails.add(n.get("id"))

    if not tails:
        return None

    tail_node = max(thread_nodes, key=lambda n: n.get("beat_index", 0))
    return {
        "id": tail_node.get("id", ""),
        "timeline_anchor": tail_node.get("timeline_anchor", ""),
        "beat_index": tail_node.get("beat_index", 0),
    }


def search_nodes_impl(book_id: str, keyword: str, **kwargs) -> list[dict]:
    """Search nodes by character name (T3 implementation)."""
    nodes_file = f"data/books/{book_id}/nodes.json"

    try:
        nodes_data = json_storage.read(nodes_file) or []
    except Exception:
        return []

    # Handle both list format and dict format
    if isinstance(nodes_data, dict):
        nodes_list = nodes_data.get("nodes", [])
    else:
        nodes_list = nodes_data

    results = []
    for n in nodes_list:
        characters = n.get("characters", [])
        char_names = [c.get("name", "") for c in characters if c.get("name")]
        if any(keyword in name for name in char_names):
            results.append({
                "id": n.get("id", ""),
                "thread_id": n.get("thread_id", ""),
                "scene": (n.get("scene", "") or "")[:50],
                "characters": char_names,
            })
    return results


TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
}
