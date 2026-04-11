from typing import List, Optional
from src.models.narrative_node import NarrativeNode, StoryStructure
from src.services.interfaces import INodeService
from src.storage.database import Database
from src.storage.json_storage import JsonStorage


class NodeService(INodeService):
    def __init__(self, db: Database, json_storage: JsonStorage):
        self.db = db
        self.json_storage = json_storage

    def save_nodes(self, book_id: str, nodes: List[NarrativeNode], structure: StoryStructure) -> None:
        """保存节点到 JSON 文件"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        data = {
            "book_id": book_id,
            "nodes": [node.model_dump() for node in nodes],
            "structure": structure.model_dump()
        }
        self.json_storage.write(book.nodes_file_path, data)

    def get_nodes(self, book_id: str) -> List[NarrativeNode]:
        """获取书籍所有节点"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        try:
            data = self.json_storage.read(book.nodes_file_path)
        except FileNotFoundError:
            return []

        return [NarrativeNode.model_validate(n) for n in data.get("nodes", [])]

    def get_node(self, book_id: str, node_id: str) -> Optional[NarrativeNode]:
        """获取单个节点"""
        nodes = self.get_nodes(book_id)
        for node in nodes:
            if node.id == node_id:
                return node
        return None

    def get_structure(self, book_id: str) -> Optional[StoryStructure]:
        """获取故事结构"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        try:
            data = self.json_storage.read(book.nodes_file_path)
        except FileNotFoundError:
            return None

        if "structure" in data:
            return StoryStructure.model_validate(data["structure"])
        return None