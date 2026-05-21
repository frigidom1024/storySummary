"""LangChain tool signatures for node history queries.

These functions are declaration-only. Runtime implementations are in
`src.core.tools.tool_executor`.
"""

from langchain_core.tools import tool
from src.models.narrative_node import ToolResponseNode, VectorSearchNode
from src.analysis.tools.tool_executor import get_previous_chunk_nodes_impl, search_nodes_impl, get_thread_last_node_impl

def _inject_docs(func):
    """Inject real documentation into tool description at import time."""
    docs = ToolResponseNode.get_docs()
    func.description = func.description.format(**{"ToolResponseNode_docs": docs})
    return func


@_inject_docs
@tool
def get_previous_chunk_nodes(book_id: str) -> list[dict]:
    """Return all nodes from the latest processed chunk.

    Use this tool to understand immediate historical context before generating
    nodes for the current chunk.

    Returns:
        A list of node summaries. Each summary contains:
        {ToolResponseNode_docs}
    """
    return get_previous_chunk_nodes_impl(book_id)


@_inject_docs
@tool
def get_thread_last_node(book_id: str, thread_id: str) -> dict | None:
    """Return the newest node in a thread.

    Use this tool to assign `thread_prev_node_id` when appending a new node to
    an existing thread.

    Returns:
        {ToolResponseNode_docs}
    """
    return get_thread_last_node_impl(book_id, thread_id)

@tool
def _search_nodes_decl(book_id: str, keyword: str) -> list[dict]:
    """Search historical nodes with a fuzzy keyword match.

    The keyword is matched against character names and scene/event text.

    Returns:
        A list of node summaries using the same schema as
        {VectorSearchNode_docs}
    """
    return search_nodes_impl(book_id=book_id, keyword=keyword)

_search_nodes_decl.description = _search_nodes_decl.description.format(**{"VectorSearchNode_docs": VectorSearchNode.get_docs()})
search_nodes = _search_nodes_decl