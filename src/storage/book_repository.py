"""书籍仓储接口 - 通过 book_id 管理 chunks 和 nodes 的 JSON 文件存储"""

from typing import List, Optional
from pathlib import Path

from src.storage.json_storage import JsonStorage
from src.models.narrative_node import NarrativeNode
from src.models.chunk import Chunk


class BookRepository:
    """书籍仓储 - 管理书籍的 chunks 和 nodes"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.json_storage = JsonStorage()

    def _book_dir(self, book_id: str) -> Path:
        """获取书籍目录路径"""
        return self.base_dir / "books" / book_id

    def _nodes_file(self, book_id: str) -> str:
        """获取 nodes.json 文件路径"""
        return str(self._book_dir(book_id) / "nodes.json")

    def _chunks_file(self, book_id: str) -> str:
        """获取 chunks.json 文件路径"""
        return str(self._book_dir(book_id) / "chunks.json")

    # === Chunks ===

    def save_chunks(self, book_id: str, chunks: List[Chunk]) -> None:
        """保存 chunks 到 JSON 文件"""
        self._book_dir(book_id).mkdir(parents=True, exist_ok=True)
        data = [
            {
                "id": c.id,
                "text": c.text,
                "chapter": c.chapter,
                "order": c.order,
            }
            for c in chunks
        ]
        self.json_storage.write(self._chunks_file(book_id), data)

    def load_chunks(self, book_id: str) -> List[Chunk]:
        """从 JSON 文件加载 chunks"""
        try:
            data = self.json_storage.read(self._chunks_file(book_id))
            if isinstance(data, list):
                return [
                    Chunk(
                        id=item.get("id", ""),
                        text=item.get("text", ""),
                        chapter=item.get("chapter", ""),
                        order=item.get("order", 0),
                    )
                    for item in data
                ]
            return []
        except FileNotFoundError:
            return []

    def append_chunk(self, book_id: str, chunk: Chunk) -> None:
        """追加单个 chunk 到文件"""
        chunks = self.load_chunks(book_id)
        chunks.append(chunk)
        self.save_chunks(book_id, chunks)

    # === Nodes ===

    def save_nodes(self, book_id: str, nodes: List[NarrativeNode]) -> None:
        """保存 nodes 到 JSON 文件"""
        self._book_dir(book_id).mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [node.to_dict() for node in nodes]
        }
        self.json_storage.write(self._nodes_file(book_id), data)

    def load_nodes(self, book_id: str) -> List[NarrativeNode]:
        """从 JSON 文件加载 nodes"""
        try:
            data = self.json_storage.read(self._nodes_file(book_id))
            if isinstance(data, dict):
                nodes_list = data.get("nodes", [])
            else:
                nodes_list = data if isinstance(data, list) else []

            return [NarrativeNode(**n) for n in nodes_list]
        except FileNotFoundError:
            return []

    def append_node(self, book_id: str, node: NarrativeNode) -> None:
        """追加单个 node 到文件"""
        nodes = self.load_nodes(book_id)
        nodes.append(node)
        self.save_nodes(book_id, nodes)

    def get_node(self, book_id: str, node_id: str) -> Optional[NarrativeNode]:
        """根据 node_id 获取单个 node"""
        nodes = self.load_nodes(book_id)
        for n in nodes:
            if n.id == node_id:
                return n
        return None

    def get_nodes_by_chunk(self, book_id: str, chunk_id: str) -> List[NarrativeNode]:
        """获取指定 chunk 的所有 nodes"""
        nodes = self.load_nodes(book_id)
        return [n for n in nodes if n.parent_chunk_id == chunk_id]

    def get_nodes_by_thread(self, book_id: str, thread_id: str) -> List[NarrativeNode]:
        """获取指定 thread 的所有 nodes"""
        nodes = self.load_nodes(book_id)
        return [n for n in nodes if n.thread_id == thread_id]

    # === Bulk operations ===

    def node_exists(self, book_id: str, node_id: str) -> bool:
        """检查 node 是否存在"""
        return self.get_node(book_id, node_id) is not None

    def clear_nodes(self, book_id: str) -> None:
        """清空 nodes 文件"""
        self.save_nodes(book_id, [])

    def clear_chunks(self, book_id: str) -> None:
        """清空 chunks 文件"""
        self.save_chunks(book_id, [])