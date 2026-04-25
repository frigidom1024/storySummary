from typing import List, Optional
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.services.interfaces import INodeService
from src.storage.database import Database
from src.storage.book_repository import book_repository


class NodeService(INodeService):
    def __init__(self, db: Database):
        self.db = db

    def save_nodes(self, book_id: str, nodes: List[NarrativeNode], structure: StoryStructure = None) -> None:
        """保存节点到 JSON 文件"""
        # 使用 BookRepository 保存 nodes
        book_repository.save_nodes(book_id, nodes)

        # 保存 structure（如果提供）
        if structure:
            structure_data = structure.model_dump()
            nodes_dir = f"data/books/{book_id}"
            import os
            os.makedirs(nodes_dir, exist_ok=True)
            structure_file = f"{nodes_dir}/structure.json"
            import json
            with open(structure_file, 'w', encoding='utf-8') as f:
                json.dump(structure_data, f, ensure_ascii=False, indent=2)

    def get_nodes(self, book_id: str) -> List[NarrativeNode]:
        """获取书籍所有节点"""
        return book_repository.load_nodes(book_id)

    def get_node(self, book_id: str, node_id: str) -> Optional[NarrativeNode]:
        """获取单个节点"""
        nodes = self.get_nodes(book_id)
        for node in nodes:
            if node.id == node_id:
                return node
        return None

    def get_structure(self, book_id: str) -> Optional[StoryStructure]:
        """获取故事结构"""
        nodes_dir = f"data/books/{book_id}"
        structure_file = f"{nodes_dir}/structure.json"
        try:
            import json
            with open(structure_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        if "structure" in data:
            return StoryStructure.model_validate(data["structure"])
        return None