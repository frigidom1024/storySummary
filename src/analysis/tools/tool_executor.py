"""Tool runtime implementations for node history querying."""

from __future__ import annotations

from typing import Any

from src.models.narrative_node import NarrativeNode
from src.storage.book_repository import book_repository
from src.storage.vector_store import VectorStore


def _safe_load_nodes(book_id: str) -> list[Any]:
    try:
        return book_repository.load_nodes(book_id)
    except Exception:
        return []


def _safe_load_chunks(book_id: str) -> list[Any]:
    try:
        return book_repository.load_chunks(book_id)
    except Exception:
        return []


def _character_names(node: Any) -> list[str]:
    names: list[str] = []
    for character in getattr(node, "characters", []) or []:
        name = getattr(character, "name", "")
        if name:
            names.append(name)
    return names


def _keyword_search_nodes(book_id: str, keyword: str) -> list[dict[str, Any]]:
    normalized = (keyword or "").strip().lower()
    if not normalized:
        return []

    all_nodes = _safe_load_nodes(book_id)
    results: list[dict[str, Any]] = []
    for node in all_nodes:
        characters = _character_names(node)
        scene = getattr(node, "scene", "") or ""
        event_summary = getattr(node, "event_summary", "") or ""
        haystack = " ".join(characters + [scene, event_summary]).lower()
        if normalized in haystack:
            summary = _node_summary(node)
            summary["scene"] = summary.get("scene", "")[:80]
            results.append(summary)
    return results


def _node_summary(node: NarrativeNode) -> dict[str, Any]:
    return node.to_tool_response()


_vector_store = VectorStore("data/vectors")


def get_previous_chunk_nodes_impl(book_id: str, **_: Any) -> list[dict[str, Any]]:
    """Return all nodes from the latest processed chunk."""
    chunks = _safe_load_chunks(book_id)
    if not chunks:
        return []

    last_chunk = max(chunks, key=lambda c: getattr(c, "order", 0))
    last_chunk_id = getattr(last_chunk, "id", "")
    if not last_chunk_id:
        return []

    all_nodes = _safe_load_nodes(book_id)
    return [
        _node_summary(node)
        for node in all_nodes
        if getattr(node, "parent_chunk_id", "") == last_chunk_id
    ]


def get_thread_last_node_impl(
    book_id: str,
    thread_id: str,
    **_: Any,
) -> dict[str, Any] | None:
    """Return the newest node in the requested thread."""
    all_nodes = _safe_load_nodes(book_id)
    thread_nodes = [node for node in all_nodes if getattr(node, "thread_id", "") == thread_id]
    if not thread_nodes:
        return None

    # Prefer linked-list tail (node not referenced by another node's `thread_next_node_id`).
    all_next_ids = {
        getattr(node, "thread_next_node_id", "")
        for node in thread_nodes
        if getattr(node, "thread_next_node_id", "")
    }
    tail_candidates = [node for node in thread_nodes if getattr(node, "id", "") not in all_next_ids]
    target_pool = tail_candidates or thread_nodes

    # Stable ordering by beat_index, fallback to lexicographic node id.
    last_node = max(
        target_pool,
        key=lambda node: (
            int(getattr(node, "beat_index", 0) or 0),
            str(getattr(node, "id", "")),
        ),
    )
    return _node_summary(last_node)


def search_nodes_impl(book_id: str, keyword: str, **_: Any) -> list[dict[str, Any]]:
    """Vector-search historical nodes by semantic similarity."""
    query = (keyword or "").strip()
    if not query:
        return []

    all_nodes = _safe_load_nodes(book_id)
    if not all_nodes:
        return []
    node_by_id = {getattr(node, "id", ""): node for node in all_nodes if getattr(node, "id", "")}

    try:
        docs = _vector_store.query_nodes(book_id=book_id, query_text=query, n_results=8)
    except Exception:
        return _keyword_search_nodes(book_id, query)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        node_id = str(metadata.get("node_id") or metadata.get("id") or "").strip()
        if not node_id or node_id in seen_ids:
            continue
        node = node_by_id.get(node_id)
        if node is None:
            continue
        summary = _node_summary(node)
        summary["scene"] = summary.get("scene", "")
        results.append(summary)
        seen_ids.add(node_id)

    if results:
        return results
    return _keyword_search_nodes(book_id, query)


def get_existing_threads_impl(
    book_id: str,
    last_node_number: int = 3,
    **_: Any,
) -> list[dict[str, Any]]:
    """Return all existing threads with latest nodes summaries."""
    all_nodes = _safe_load_nodes(book_id)
    if not all_nodes:
        return []

    threads: dict[str, list[NarrativeNode]] = {}
    for node in all_nodes:
        thread_id = (getattr(node, "thread_id", "") or "main").strip() or "main"
        threads.setdefault(thread_id, []).append(node)

    results: list[dict[str, Any]] = []
    for thread_id, nodes in threads.items():
        # Sort by beat_index descending to get the latest nodes first
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (
                int(getattr(n, "beat_index", 0) or 0),
                str(getattr(n, "id", "")),
            ),
            reverse=True,
        )
        last_nodes = [_node_summary(n) for n in sorted_nodes[:last_node_number]]
        last_node = last_nodes[0] if last_nodes else None
        results.append(
            {
                "thread_id": thread_id,
                "thread_name": getattr(sorted_nodes[0], "thread_name", "") if sorted_nodes else thread_id,
                "node_count": len(nodes),
                "nodes": last_nodes,
                "last_node": last_node,
            }
        )

    results.sort(key=lambda item: item["thread_id"])
    return results


def get_all_nodes_in_thread_impl(book_id: str, thread_id: str, **_: Any) -> list[dict[str, Any]]:
    """Return all nodes in a thread, ordered by beat index."""
    target_thread = (thread_id or "").strip()
    if not target_thread:
        return []

    all_nodes = _safe_load_nodes(book_id)
    thread_nodes = [n for n in all_nodes if (getattr(n, "thread_id", "") or "main") == target_thread]
    thread_nodes.sort(key=lambda n: (int(getattr(n, "beat_index", 0) or 0), str(getattr(n, "id", ""))))
    return [_node_summary(node) for node in thread_nodes]




TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
    "get_existing_threads": get_existing_threads_impl,
    "get_all_nodes_in_thread": get_all_nodes_in_thread_impl,
}

