"""Story graph helper for querying multi-thread narratives."""
from src.models.narrative_node import NarrativeNode


class StoryGraph:
    """
    Helper class to query and traverse a story graph with multiple threads.

    Supports:
    - Get all threads (story lines)
    - Get nodes in a specific thread (via thread_prev_node_id chain)
    - Get nodes in original text order (via prev_node_id chain)
    - Get nodes in story-chronological order (timeline_order)
    - Get convergence points
    - Query by character
    """

    def __init__(self, nodes: list[NarrativeNode]):
        self.nodes = nodes
        self._node_map: dict[str, NarrativeNode] = {}
        self._thread_index: dict[str, list[NarrativeNode]] = {}
        self._build_indices()

    def _build_indices(self):
        """Build lookup indices from nodes."""
        for node in self.nodes:
            self._node_map[node.id] = node
            if node.thread_id not in self._thread_index:
                self._thread_index[node.thread_id] = []
            self._thread_index[node.thread_id].append(node)

    def get_threads(self) -> list[str]:
        """Get all thread IDs in this story."""
        return list(self._thread_index.keys())

    def get_thread(self, thread_id: str) -> list[NarrativeNode]:
        """
        Get all nodes in a thread, in story order (via thread_prev_node_id chain).

        Traverses using thread_prev_node_id links. If no links exist,
        falls back to chunk order.
        """
        thread_nodes = self._thread_index.get(thread_id, [])
        if not thread_nodes:
            return []

        # Find the head (node with empty thread_prev_node_id)
        head = None
        for n in thread_nodes:
            if not n.thread_prev_node_id:
                head = n
                break

        if not head:
            # No links found, return in chunk order
            return sorted(thread_nodes, key=lambda n: n.beat_index)

        # Traverse via thread_prev_node_id links
        result = []
        current = head
        while current:
            result.append(current)
            # Find next via thread_next_node_id first (forward link)
            if current.thread_next_node_id:
                current = self._node_map.get(current.thread_next_node_id)
            else:
                # Fall back: find node whose thread_prev_node_id == current.id
                current = None
                for n in thread_nodes:
                    if n.thread_prev_node_id == result[-1].id and n not in result:
                        current = n
                        break

        return result

    def get_text_order(self) -> list[NarrativeNode]:
        """
        Get all nodes in original text/chunk order (via prev_node_id chain).
        """
        if not self.nodes:
            return []

        # Find head (node with empty prev_node_id)
        head = None
        for n in self.nodes:
            if not n.prev_node_id:
                head = n
                break

        if not head:
            return list(self.nodes)

        # Traverse via prev_node_id links
        result = []
        current = head
        visited = set()
        while current and current.id not in visited:
            result.append(current)
            visited.add(current.id)
            current = self._node_map.get(current.prev_node_id) if current.prev_node_id else None

        return result

    def get_timeline_order(self) -> list[NarrativeNode]:
        """
        Get all nodes sorted by story-chronological order (timeline_order ASC).
        For same timeline_order, preserve relative order.
        """
        return sorted(self.nodes, key=lambda n: (n.timeline_order, n.beat_index))

    def get_convergence_points(self) -> list[NarrativeNode]:
        """Get all multi-thread convergence nodes."""
        return [n for n in self.nodes if n.is_convergence]

    def get_node_by_id(self, node_id: str) -> NarrativeNode | None:
        """Lookup node by ID."""
        return self._node_map.get(node_id)

    def get_nodes_for_character(self, character_name: str) -> list[NarrativeNode]:
        """Get all nodes where a character appears."""
        return [
            n for n in self.nodes
            if any(c.name == character_name for c in n.characters)
        ]

    def get_character_threads(self, character_name: str) -> list[str]:
        """Get which threads a character appears in."""
        threads = set()
        for n in self.nodes:
            if any(c.name == character_name for c in n.characters):
                threads.add(n.thread_id)
        return list(threads)
