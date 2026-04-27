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

    # === Outline ===

    def save_outline(self, book_id: str, outline: dict) -> None:
        """保存口播稿大纲（结构化 JSON）"""
        self._write_json(self._outline_file(book_id), outline)

    def load_outline(self, book_id: str) -> dict | None:
        """加载口播稿大纲"""
        file_path = self._outline_file(book_id)
        if not file_path.exists():
            return None
        return self.json_storage.read(str(file_path))

    # === Synopsis ===

    def save_synopsis(self, book_id: str, synopsis: str) -> None:
        """保存故事梗概"""
        data = {"synopsis": synopsis}
        self._write_json(self._synopsis_file(book_id), data)

    def load_synopsis(self, book_id: str) -> str | None:
        """加载故事梗概"""
        file_path = self._synopsis_file(book_id)
        if not file_path.exists():
            return None
        data = self.json_storage.read(str(file_path))
        if isinstance(data, dict):
            return data.get("synopsis", "")
        return None

    # === Chapter Drafts ===

    def save_chapter_draft(self, book_id: str, chapter_id: str, draft: str) -> None:
        """保存单个章节草稿"""
        drafts = self.load_all_drafts(book_id)
        drafts[chapter_id] = draft
        self._write_json(self._drafts_file(book_id), drafts)

    def load_chapter_draft(self, book_id: str, chapter_id: str) -> str | None:
        """加载单个章节草稿"""
        drafts = self.load_all_drafts(book_id)
        return drafts.get(chapter_id)

    def save_all_drafts(self, book_id: str, drafts: dict[str, str]) -> None:
        """批量保存章节草稿"""
        self._write_json(self._drafts_file(book_id), drafts)

    def load_all_drafts(self, book_id: str) -> dict[str, str]:
        """加载所有章节草稿"""
        file_path = self._drafts_file(book_id)
        if not file_path.exists():
            return {}
        data = self.json_storage.read(str(file_path))
        if isinstance(data, dict):
            return data
        return {}

    # === Final Manuscript ===

    def save_final_manuscript(self, book_id: str, manuscript: str) -> None:
        """保存最终口播稿"""
        file_path = self._final_manuscript_file(book_id)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(manuscript, encoding="utf-8")

    def load_final_manuscript(self, book_id: str) -> str | None:
        """加载最终口播稿"""
        file_path = self._final_manuscript_file(book_id)
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8")

    # === Utility ===

    def delete_manuscript(self, book_id: str) -> None:
        """删除口播稿相关所有文件"""
        files = [
            self._synopsis_file(book_id),
            self._outline_file(book_id),
            self._drafts_file(book_id),
            self._final_manuscript_file(book_id),
        ]
        for file_path in files:
            if file_path.exists():
                file_path.unlink()

    def manuscript_exists(self, book_id: str) -> bool:
        """检查口播稿是否已生成（至少存在大纲文件）"""
        return self._outline_file(book_id).exists()