"""Tool implementations — read from BookStorage."""

from src.storage.book_storage import BookStorage

book_storage = BookStorage()


def get_previous_chunk_nodes_impl(book_id: str, **kwargs) -> list[dict]:
    """Get all nodes from the previous chunk (T1 implementation)."""
    try:
        chunks = book_storage.load_chunks(book_id)
    except Exception:
        return []

    if not chunks:
        return []

    last_chunk = max(chunks, key=lambda c: c.order)
    last_chunk_id = last_chunk.id
    if not last_chunk_id:
        return []

    try:
        all_nodes = book_storage.load_nodes(book_id)
    except Exception:
        return []

    prev_nodes = [
        {
            "id": n.id,
            "timeline_anchor": n.timeline_anchor,
            "thread_id": n.thread_id,
            "characters": [c.name for c in n.characters if c.name],
            "narrative_role": n.narrative_role,
        }
        for n in all_nodes
        if n.parent_chunk_id == last_chunk_id
    ]
    return prev_nodes


def get_thread_last_node_impl(book_id: str, thread_id: str, **kwargs) -> dict | None:
    """Get the last node in a thread chain (T2 implementation)."""
    try:
        all_nodes = book_storage.load_nodes(book_id)
    except Exception:
        return None

    thread_nodes = [n for n in all_nodes if n.thread_id == thread_id]
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


def search_nodes_impl(book_id: str, keyword: str, **kwargs) -> list[dict]:
    """Search nodes by character name (T3 implementation)."""
    try:
        all_nodes = book_storage.load_nodes(book_id)
    except Exception:
        return []

    results = []
    for n in all_nodes:
        char_names = [c.name for c in n.characters if c.name]
        if any(keyword in name for name in char_names):
            results.append({
                "id": n.id,
                "thread_id": n.thread_id,
                "scene": (n.scene or "")[:50],
                "characters": char_names,
            })
    return results


TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
}
