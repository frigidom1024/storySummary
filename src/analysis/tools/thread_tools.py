"""LangChain tool signatures for thread query tools.

These functions are declaration-only. Runtime implementations are in
`src.core.tools.tool_executor`.
"""

from langchain_core.tools import tool
from src.models.narrative_node import ToolResponseNode
from src.analysis.tools.tool_executor import get_previous_chunk_nodes_impl, search_nodes_impl, get_thread_last_node_impl

def _inject_docs(func):
    """Inject real documentation into tool description at import time."""
    docs = ToolResponseNode.get_docs()
    func.description = func.description.format(**{"ToolResponseNode_docs": docs})
    return func


@tool
def _get_existing_threads_decl(book_id: str, last_node_number: int = 3) -> list[dict]:
    """Return all existing threads (with latest nodes in each thread) in this book.

    Each item contains:
    - thread_id
    - thread_name
    - nodes: last_node_number nodes summaries with {ToolResponseNode_docs}
    """
    return get_existing_threads_impl(book_id, last_node_number)

_get_existing_threads_decl.description = _get_existing_threads_decl.description.format(**{"ToolResponseNode_docs": ToolResponseNode.get_docs()})
get_existing_threads = _get_existing_threads_decl


@_inject_docs
@tool
def get_all_nodes_in_thread(book_id: str, thread_id: str) -> list[dict]:
    """Return all nodes in one thread.

    The returned node schema are {ToolResponseNode_docs}
    """
    return get_all_nodes_in_thread_impl(book_id, thread_id)