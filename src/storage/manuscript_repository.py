"""口播稿仓储接口 - 管理口播稿工作流成果的存储"""

import json
import os
import tempfile
from pathlib import Path

from src.storage.json_storage import JsonStorage


class ManuscriptRepository:
    """口播稿仓储 - 管理口播稿工作流成果的存储"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.books_dir = self.base_dir / "books"
        self.json_storage = JsonStorage()

    # === 路径构建 ===

    def _book_dir(self, book_id: str) -> Path:
        """获取书籍目录路径"""
        return self.books_dir / book_id

    def _synopsis_file(self, book_id: str) -> Path:
        """获取 synopsis.json 路径"""
        return self._book_dir(book_id) / "synopsis.json"

    def _outline_file(self, book_id: str) -> Path:
        """获取 outline.json 路径"""
        return self._book_dir(book_id) / "outline.json"

    def _drafts_file(self, book_id: str) -> Path:
        """获取 chapter_drafts.json 路径"""
        return self._book_dir(book_id) / "chapter_drafts.json"

    def _final_manuscript_file(self, book_id: str) -> Path:
        """获取 final_manuscript.txt 路径"""
        return self._book_dir(book_id) / "final_manuscript.txt"

    # === 原子写入 ===

    def _write_json(self, file_path: Path, data) -> None:
        """原子写入 JSON 文件"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=file_path.parent)
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, file_path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise