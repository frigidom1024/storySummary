"""Tool definitions using langchain_core @tool decorator."""

from langchain_core.tools import tool


@tool
def get_previous_chunk_nodes(book_id: str) -> list[dict]:
    """Get all nodes from the previous chunk.

    Use this to understand the time anchor (timeline_anchor) of the
    chunk that came before the current one.

    "Previous chunk" means the chunk immediately before the current
    one in sequential processing order. Only one chunk's nodes are returned.

    Returns:
        list of dicts with keys:
        - id: node ID
        - timeline_anchor: time anchor string (e.g., "现在", "一年前")
        - thread_id: thread identifier
        - characters: list of character names in this node
        - narrative_role: opening/rising/climax/ending

    Note: scene text is NOT returned (too large). Use search_nodes for scene search.
    """
    raise NotImplementedError("Implemented in tool_executor.py")


@tool
def get_thread_last_node(book_id: str, thread_id: str) -> dict | None:
    """Get the last (newest) node in a given thread's chain.

    Use this to fill in thread_prev_node_id when creating a new node
    in an existing thread. The returned node is the tail of the
    thread_prev_node_id linked list.

    Args:
        book_id: which book to search
        thread_id: e.g. 'main', 'zhang', 'chenwei', 'laozhou'

    Returns:
        dict with keys: id, timeline_anchor, beat_index
        or None if this thread has no previous nodes (i.e., this is the first node in this thread)
    """
    raise NotImplementedError("Implemented in tool_executor.py")


@tool
def search_nodes(book_id: str, keyword: str) -> list[dict]:
    """Search nodes by character name or scene keyword.

    Uses SQLite LIKE matching (not vector search). Keyword matches
    against character names in nodes.

    Use this to find which thread a character belongs to, to correctly
    assign thread_id for a new node.

    Args:
        book_id: which book to search
        keyword: character name to search for

    Returns:
        list of dicts with keys: id, thread_id, scene (truncated to 50 chars), characters
    """
    raise NotImplementedError("Implemented in tool_executor.py")
