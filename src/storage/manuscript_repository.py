"""口播稿仓储接口 - 管理口播稿工作流成果的存储"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from src.storage.json_storage import JsonStorage


class ManuscriptRepository:
    """口播稿仓储 - 管理口播稿工作流成果的存储"""

    # 草稿类型常量
    DRAFT_TYPE_INTRO = "intro"           # 开篇介绍 - GuideAgent
    DRAFT_TYPE_CHAPTER = "chapter"       # 章节正文 - ChapterWriter
    DRAFT_TYPE_REFLECTION = "reflection" # 总结思考 - GuideAgent

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.books_dir = self.base_dir / "books"
        self.json_storage = JsonStorage()

    # === 路径构建 ===

    def _book_dir(self, book_id: str) -> Path:
        return self.books_dir / book_id

    def _drafts_file(self, book_id: str) -> Path:
        """统一的草稿文件"""
        return self._book_dir(book_id) / "drafts.json"

    def _style_profile_file(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "style_profile.json"

    def _chapter_summaries_file(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "chapter_summaries.txt"

    def _synopsis_file(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "synopsis.json"

    def _outline_file(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "outline.json"

    def _final_manuscript_file(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "final_manuscript.txt"

    def _metadata_file(self, book_id: str) -> Path:
        return self._book_dir(book_id) / "manuscript_metadata.json"

    # === 原子写入 ===

    def _write_json(self, file_path: Path, data) -> None:
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

    def _write_text(self, file_path: Path, text: str) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding="utf-8")

    def _read_text(self, file_path: Path) -> Optional[str]:
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8")

    # ====================== 统一草稿管理 ======================
    # 所有草稿（intro/chapter/reflection）统一存储，按 section_id 索引

    def save_draft(self, book_id: str, section_id: str, draft_type: str, content: str) -> None:
        """保存单个草稿

        Args:
            book_id: 书籍ID
            section_id: 章节/部分ID（如 "intro", "chapter-1", "reflection"）
            draft_type: 草稿类型 ("intro" | "chapter" | "reflection")
            content: 草稿正文
        """
        drafts = self.load_all_drafts(book_id)
        drafts[section_id] = {
            "type": draft_type,
            "content": content,
        }
        self._write_json(self._drafts_file(book_id), drafts)

    def load_draft(self, book_id: str, section_id: str) -> Optional[dict]:
        """加载单个草稿

        Returns:
            {"type": str, "content": str} 或 None
        """
        drafts = self.load_all_drafts(book_id)
        return drafts.get(section_id)

    def save_all_drafts(self, book_id: str, drafts: dict[str, dict]) -> None:
        """批量保存草稿

        Args:
            book_id: 书籍ID
            drafts: {section_id: {"type": str, "content": str}, ...}
        """
        self._write_json(self._drafts_file(book_id), drafts)

    def load_all_drafts(self, book_id: str) -> dict[str, dict]:
        """加载所有草稿

        Returns:
            {section_id: {"type": str, "content": str}, ...}
        """
        file_path = self._drafts_file(book_id)
        if not file_path.exists():
            return {}
        data = self.json_storage.read(str(file_path))
        if isinstance(data, dict):
            return data
        return {}

    def get_drafts_by_type(self, book_id: str, draft_type: str) -> dict[str, dict]:
        """获取指定类型的所有草稿

        Args:
            book_id: 书籍ID
            draft_type: "intro" | "chapter" | "reflection"

        Returns:
            {section_id: {"type": str, "content": str}, ...}
        """
        all_drafts = self.load_all_drafts(book_id)
        return {
            section_id: draft
            for section_id, draft in all_drafts.items()
            if draft.get("type") == draft_type
        }

    # ====================== 其他存储 ======================

    def save_style_profile(self, book_id: str, style_profile: dict) -> None:
        """保存风格画像"""
        self._write_json(self._style_profile_file(book_id), style_profile)

    def load_style_profile(self, book_id: str) -> Optional[dict]:
        file_path = self._style_profile_file(book_id)
        if not file_path.exists():
            return None
        return self.json_storage.read(str(file_path))

    def save_chapter_summaries(self, book_id: str, summaries: str) -> None:
        self._write_text(self._chapter_summaries_file(book_id), summaries)

    def load_chapter_summaries(self, book_id: str) -> Optional[str]:
        return self._read_text(self._chapter_summaries_file(book_id))

    def save_synopsis(self, book_id: str, synopsis: str) -> None:
        self._write_json(self._synopsis_file(book_id), {"synopsis": synopsis})

    def load_synopsis(self, book_id: str) -> Optional[str]:
        file_path = self._synopsis_file(book_id)
        if not file_path.exists():
            return None
        data = self.json_storage.read(str(file_path))
        if isinstance(data, dict):
            return data.get("synopsis", "")
        return None

    def save_outline(self, book_id: str, outline: dict) -> None:
        self._write_json(self._outline_file(book_id), outline)

    def load_outline(self, book_id: str) -> Optional[dict]:
        file_path = self._outline_file(book_id)
        if not file_path.exists():
            return None
        return self.json_storage.read(str(file_path))

    def save_final_manuscript(self, book_id: str, manuscript: str) -> None:
        self._write_text(self._final_manuscript_file(book_id), manuscript)

    def load_final_manuscript(self, book_id: str) -> Optional[str]:
        return self._read_text(self._final_manuscript_file(book_id))

    def save_metadata(self, book_id: str, metadata: dict) -> None:
        self._write_json(self._metadata_file(book_id), metadata)

    def load_metadata(self, book_id: str) -> Optional[dict]:
        file_path = self._metadata_file(book_id)
        if not file_path.exists():
            return None
        return self.json_storage.read(str(file_path))

    def update_metadata(self, book_id: str, updates: dict) -> None:
        current = self.load_metadata(book_id) or {}
        current.update(updates)
        self.save_metadata(book_id, current)

    # ====================== 状态检查 ======================

    def has_style_profile(self, book_id: str) -> bool:
        return self._style_profile_file(book_id).exists()

    def has_synopsis(self, book_id: str) -> bool:
        return self._synopsis_file(book_id).exists()

    def has_outline(self, book_id: str) -> bool:
        return self._outline_file(book_id).exists()

    def has_final_manuscript(self, book_id: str) -> bool:
        return self._final_manuscript_file(book_id).exists()

    def manuscript_status(self, book_id: str) -> dict:
        """获取口播稿生成状态"""
        all_drafts = self.load_all_drafts(book_id)
        intro_drafts = self.get_drafts_by_type(book_id, self.DRAFT_TYPE_INTRO)
        chapter_drafts = self.get_drafts_by_type(book_id, self.DRAFT_TYPE_CHAPTER)
        reflection_drafts = self.get_drafts_by_type(book_id, self.DRAFT_TYPE_REFLECTION)

        return {
            "style_profile": self.has_style_profile(book_id),
            "synopsis": self.has_synopsis(book_id),
            "outline": self.has_outline(book_id),
            "drafts": {
                "intro": len(intro_drafts),
                "chapter": len(chapter_drafts),
                "reflection": len(reflection_drafts),
                "total": len(all_drafts),
            },
            "final_manuscript": self.has_final_manuscript(book_id),
        }

    # ====================== 删除 ======================

    def delete_manuscript(self, book_id: str) -> None:
        files = [
            self._drafts_file(book_id),
            self._style_profile_file(book_id),
            self._chapter_summaries_file(book_id),
            self._synopsis_file(book_id),
            self._outline_file(book_id),
            self._final_manuscript_file(book_id),
            self._metadata_file(book_id),
        ]
        for file_path in files:
            if file_path.exists():
                file_path.unlink()

    def manuscript_exists(self, book_id: str) -> bool:
        return self.has_outline(book_id)


manuscript_repository = ManuscriptRepository()