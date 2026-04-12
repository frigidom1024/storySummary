from typing import List, Optional
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.services.interfaces import INodeService
from src.storage.database import Database
from src.storage.json_storage import JsonStorage


class NodeService(INodeService):
    def __init__(self, db: Database, json_storage: JsonStorage):
        self.db = db
        self.json_storage = json_storage

    def save_nodes(self, book_id: str, nodes: List[NarrativeNode], structure: StoryStructure = None) -> None:
        """保存节点到 JSON 文件"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        data = {
            "book_id": book_id,
            "nodes": [node.model_dump() for node in nodes],
            "structure": structure.model_dump() if structure else None
        }
        nodes_file = f"{book.nodes_file_path}/nodes.json"
        self.json_storage.write(nodes_file, data)

    def get_nodes(self, book_id: str) -> List[NarrativeNode]:
        """获取书籍所有节点"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        try:
            nodes_file = f"{book.nodes_file_path}/nodes.json"
            data = self.json_storage.read(nodes_file)
        except FileNotFoundError:
            return []

        # 支持两种格式：列表或 {"nodes": [...]} 字典
        if isinstance(data, list):
            nodes_list = data
        else:
            nodes_list = data.get("nodes", []) if isinstance(data, dict) else []

        return [NarrativeNode.model_validate(n) for n in nodes_list]

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
            structure_file = f"{book.nodes_file_path}/structure.json"
            data = self.json_storage.read(structure_file)
        except FileNotFoundError:
            return None

        if not isinstance(data, dict):
            return None

        if "structure" in data:
            return StoryStructure.model_validate(data["structure"])
        return None