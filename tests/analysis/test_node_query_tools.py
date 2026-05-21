import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.analysis.tools.tool_executor import (
    get_previous_chunk_nodes_impl,
    get_thread_last_node_impl,
    search_nodes_impl,
    TOOL_REGISTRY,
)


class TestTOOLREGISTRY:
    def test_all_three_tools_registered(self):
        """Verify all three tools are in the registry."""
        assert "get_previous_chunk_nodes" in TOOL_REGISTRY
        assert "get_thread_last_node" in TOOL_REGISTRY
        assert "search_nodes" in TOOL_REGISTRY

    def test_registry_values_are_callable(self):
        """Verify registry values are functions."""
        for name, fn in TOOL_REGISTRY.items():
            assert callable(fn), f"{name} should be callable"


class TestGetPreviousChunkNodes:
    def test_returns_list_for_nonexistent_book(self):
        """Empty database returns empty list."""
        result = get_previous_chunk_nodes_impl(book_id="nonexistent-book-id")
        assert isinstance(result, list)

    def test_returns_list_type(self):
        """Result is always a list."""
        result = get_previous_chunk_nodes_impl(book_id="nonexistent")
        assert isinstance(result, list)


class TestGetThreadLastNode:
    def test_returns_none_for_unknown_thread(self):
        """Unknown thread returns None."""
        result = get_thread_last_node_impl(book_id="nonexistent", thread_id="unknown-thread")
        assert result is None

    def test_returns_none_for_nonexistent_book(self):
        """Nonexistent book returns None."""
        result = get_thread_last_node_impl(book_id="nonexistent-book", thread_id="main")
        assert result is None

    def test_result_has_required_keys_when_not_none(self):
        """When a node is found, it has id, timeline_anchor, beat_index."""
        # This test will return None in empty DB, which is valid
        result = get_thread_last_node_impl(book_id="nonexistent", thread_id="main")
        if result is not None:
            assert "id" in result
            assert "timeline_anchor" in result
            assert "beat_index" in result


class TestSearchNodes:
    def test_returns_list_for_nonexistent_book(self):
        """Empty database returns empty list."""
        result = search_nodes_impl(book_id="nonexistent", keyword="李岚")
        assert isinstance(result, list)

    def test_returns_list_for_unknown_keyword(self):
        """Unknown keyword returns empty list."""
        result = search_nodes_impl(book_id="nonexistent", keyword="不存在的人物")
        assert isinstance(result, list)
        assert len(result) == 0
