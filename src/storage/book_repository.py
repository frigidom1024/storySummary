"""书籍仓储接口 - 通过 book_id 管理书籍的所有文件存储"""

import os
import json
import shutil
import tempfile
from typing import List, Optional
from pathlib import Path

from src.storage.json_storage import JsonStorage
from src.models.narrative_node import NarrativeNode
from src.models.character_card import CharacterCard
from src.models.chunk import Chunk


class BookRepository:
    """书籍仓储 - 统一管理书籍的所有文件存储（book file, chunks, nodes, covers）"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.books_dir = self.base_dir / "books"
        self.covers_dir = self.base_dir / "covers"
        self.json_storage = JsonStorage()
        
        # 创建必要的目录
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.covers_dir.mkdir(parents=True, exist_ok=True)

    # === 路径构建 ===

    def _book_dir(self, book_id: str) -> Path:
        """获取书籍目录路径"""
        self._validate_id(book_id)
        return self.books_dir / book_id

    def _nodes_file(self, book_id: str) -> str:
        """获取 nodes.json 文件路径"""
        return str(self._book_dir(book_id) / "nodes.json")

    def _chunks_file(self, book_id: str) -> str:
        """获取 chunks.json 文件路径"""
        return str(self._book_dir(book_id) / "chunks.json")

    def _characters_file(self, book_id: str) -> str:
        """获取 characters.json 文件路径"""
        return str(self._book_dir(book_id) / "characters.json")

    def _validate_id(self, id_str: str) -> None:
        """验证 ID 格式，防止路径遍历"""
        clean = id_str.replace('-', '').replace('_', '')
        if not clean.isalnum():
            raise ValueError(f"Invalid ID format: {id_str}")

    # === JSON 原子写入 ===

    def _write_json(self, file_path: str, data) -> None:
        """原子写入 JSON 文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=path.parent)
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    # === Book Files ===

    def save_book_file(self, book_id: str, file_bytes: bytes, ext: str) -> str:
        """保存书籍文件到书籍目录"""
        book_dir = self._book_dir(book_id)
        book_dir.mkdir(parents=True, exist_ok=True)
        file_path = book_dir / f"book.{ext}"
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        return str(file_path)

    def get_book_file(self, book_id: str) -> Optional[tuple[str, str]]:
        """获取书籍文件路径和扩展名，返回 (path, ext) 或 None"""
        book_dir = self._book_dir(book_id)
        for ext in ['epub', 'txt', 'pdf']:
            file_path = book_dir / f"book.{ext}"
            if file_path.exists():
                return str(file_path), ext
        return None

    def book_file_exists(self, book_id: str) -> bool:
        """检查书籍文件是否存在"""
        return self.get_book_file(book_id) is not None

    def delete_book_file(self, book_id: str) -> bool:
        """删除书籍文件"""
        deleted = False
        book_dir = self._book_dir(book_id)
        for ext in ['epub', 'txt', 'pdf']:
            file_path = book_dir / f"book.{ext}"
            if file_path.exists():
                file_path.unlink()
                deleted = True
        return deleted

    # === Covers ===

    def save_cover(self, book_id: str, image_bytes: bytes, ext: str) -> Optional[str]:
        """保存封面图片"""
        if not image_bytes:
            return None
        cover_path = self.covers_dir / f"{book_id}.{ext}"
        with open(cover_path, 'wb') as f:
            f.write(image_bytes)
        return f"/api/covers/{book_id}.{ext}"

    def get_cover_url(self, book_id: str, ext: str) -> Optional[str]:
        """获取封面 URL"""
        cover_path = self.covers_dir / f"{book_id}.{ext}"
        if cover_path.exists():
            return f"/api/covers/{book_id}.{ext}"
        return None

    def delete_cover(self, book_id: str) -> bool:
        """删除封面"""
        deleted = False
        for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            cover_path = self.covers_dir / f"{book_id}.{ext}"
            if cover_path.exists():
                cover_path.unlink()
                deleted = True
        return deleted

    # === Chunks ===

    def save_chunks(self, book_id: str, chunks: List[Chunk]) -> None:
        """保存 chunks 到 JSON 文件"""
        data = [c.to_dict() for c in chunks]
        self._write_json(self._chunks_file(book_id), data)

    def load_chunks(self, book_id: str) -> List[Chunk]:
        """从 JSON 文件加载 chunks"""
        try:
            data = self.json_storage.read(self._chunks_file(book_id))
            if isinstance(data, list):
                return Chunk.from_list(data)
            return []
        except FileNotFoundError:
            return []

    def append_chunk(self, book_id: str, chunk: Chunk) -> None:
        """追加单个 chunk 到文件"""
        chunks = self.load_chunks(book_id)
        chunks.append(chunk)
        self.save_chunks(book_id, chunks)

    def update_chunks(self, book_id: str, chunks: List[Chunk]) -> None:
        """更新已有的 chunks（只更新传入的 chunks，保留其他）"""
        existing = {c.id: c for c in self.load_chunks(book_id)}
        existing.update({c.id: c for c in chunks})
        self.save_chunks(book_id, list(existing.values()))

    # === Nodes ===

    def save_nodes(self, book_id: str, nodes: List[NarrativeNode]) -> None:
        """保存 nodes 到 JSON 文件"""
        data = {
            "nodes": [node.to_dict() for node in nodes]
        }
        self._write_json(self._nodes_file(book_id), data)

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

    # === Characters ===

    def save_characters(self, book_id: str, characters: dict[str, CharacterCard]) -> None:
        """保存角色卡片到 JSON 文件"""
        data = {
            "characters": {
                name: card.model_dump() for name, card in characters.items()
            }
        }
        self._write_json(self._characters_file(book_id), data)

    def load_characters(self, book_id: str) -> dict[str, CharacterCard]:
        """从 JSON 文件加载角色卡片"""
        try:
            data = self.json_storage.read(self._characters_file(book_id))
            if isinstance(data, dict):
                characters_data = data.get("characters", {})
            else:
                characters_data = {}

            characters = {}
            for name, card_data in characters_data.items():
                # 确保 character_id 存在
                if "character_id" not in card_data:
                    card_data["character_id"] = name
                characters[name] = CharacterCard(**card_data)
            return characters
        except FileNotFoundError:
            return {}

    def get_character(self, book_id: str, character_name: str) -> Optional[CharacterCard]:
        """获取单个角色卡片"""
        characters = self.load_characters(book_id)
        return characters.get(character_name)

    def update_character(self, book_id: str, character: CharacterCard) -> None:
        """更新单个角色卡片"""
        characters = self.load_characters(book_id)
        characters[character.name] = character
        self.save_characters(book_id, characters)

    def clear_characters(self, book_id: str) -> None:
        """清空角色卡片文件"""
        self.save_characters(book_id, {})

    def cleanup_book_data(self, book_id: str) -> None:
        """删除书籍所有相关文件"""
        self.delete_book_file(book_id)
        self.delete_cover(book_id)
        book_dir = self._book_dir(book_id)
        if book_dir.exists():
            shutil.rmtree(book_dir)


# Singleton instance
book_repository = BookRepository()