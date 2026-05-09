import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from src.models.book import Book
from src.models.chunk import Chunk
from src.services.interfaces import IBookService
from src.storage.database import Database
from src.storage.book_repository import BookRepository
from src.utils.reader import read_book, classify_content_types
from src.logging_config import logger


class BookService(IBookService):
    def __init__(self, db: Database = None, base_dir: str = "data", max_chunk_chars: int = 20000):
        if db is None:
            db = Database()
        self.db = db
        self.book_repository = BookRepository(base_dir=base_dir)
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = 200

    def _split_text_into_chunks(self, text: str, chunk_prefix: str = "chunk", order_start: int = 0) -> List[Chunk]:
        """将文本分割为指定大小的 chunks"""
        import re
        
        if not text or len(text) <= self.max_chunk_chars:
            return [Chunk(
                id=f"ch_{order_start}",
                text=text.strip(),
                order=order_start
            )]

        sentences = []
        chinese_pattern = re.compile(r'([^。！？!?\.．;；]+[。！？!?\.．;；]?)')
        english_pattern = re.compile(r'([^.!?]+[.!?]?)')
        
        chinese_matches = chinese_pattern.findall(text)
        english_matches = english_pattern.findall(text)
        
        if len(chinese_matches) > len(english_matches):
            sentences = [s.strip() for s in chinese_matches if s.strip()]
        else:
            sentences = [s.strip() for s in english_matches if s.strip()]

        if not sentences:
            sentences = text.split('\n')
            sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            sentences = [text[i:i+200] for i in range(0, len(text), 200)]

        chunks = []
        current_text = ""
        current_order = order_start
        chunk_index = 0

        for i, sentence in enumerate(sentences):
            if len(current_text) + len(sentence) <= self.max_chunk_chars or not current_text:
                if current_text:
                    current_text += '\n'
                current_text += sentence
            else:
                chunks.append(Chunk(
                    id=f"ch_{current_order}",
                    text=current_text.strip(),
                    order=current_order
                ))
                current_order += 1
                
                overlap = ""
                if len(current_text) > self.chunk_overlap_chars:
                    overlap = current_text[-self.chunk_overlap_chars:]
                    overlap_start = overlap.rfind('\n')
                    if overlap_start != -1:
                        overlap = overlap[overlap_start+1:]
                
                if overlap:
                    current_text = overlap + '\n' + sentence
                else:
                    current_text = sentence
        
        if current_text.strip():
            chunks.append(Chunk(
                id=f"ch_{current_order}",
                text=current_text.strip(),
                order=current_order
            ))

        return chunks

    def _split_long_chapters(self, chapters: List[Chunk]) -> List[Chunk]:
        """将过长的章节分割为子章节"""
        result = []
        order = 0
        
        for chapter in chapters:
            original_chapter_id = chapter.id or f"ch_{order}"
            
            if not chapter.text or len(chapter.text) <= self.max_chunk_chars:
                chapter_copy = Chunk(
                    id=f"ch_{order}",
                    text=chapter.text,
                    chapter=chapter.chapter,
                    order=order,
                    content_type=chapter.content_type,
                    parent_chapter_id=original_chapter_id
                )
                result.append(chapter_copy)
                order += 1
                continue
            
            sub_chunks = self._split_text_into_chunks(chapter.text, f"ch_{order}", order)
            
            for i, sub_chunk in enumerate(sub_chunks):
                chapter_title = chapter.chapter or f"章节 {order}"
                result.append(Chunk(
                    id=f"ch_{order}",
                    text=sub_chunk.text,
                    chapter=f"{chapter_title}-第{i+1}节",
                    order=order,
                    content_type=chapter.content_type,
                    parent_chapter_id=original_chapter_id
                ))
                order += 1
        
        return result

    def _ensure_book(self, user_id: str, title: str) -> str:
        """Ensure a book record exists, return book_id."""
        books = self.db.get_books_for_user(user_id)
        for b in books:
            if b.title == title:
                return b.id
        
        book_id = str(uuid.uuid4())
        book = Book(
            id=book_id,
            user_id=user_id,
            title=title,
            author="",
            publisher="",
            cover_url="",
            nodes_file_path=f"data/books/{book_id}/nodes.json",
            status="processing",
            message="",
            is_deleted=False,
            created_at=datetime.now(),
        )
        self.db.create_book(book)
        
        return book_id

    async def process_file(self, book_path: str, user_id: str = "default-user", max_chunk_chars: int = None) -> dict:
        """Process a book file (EPUB or PDF) through the pipeline."""
        reader = read_book(book_path)

        book_id = self._ensure_book(user_id, reader.title)

        suffix = Path(book_path).suffix.lower()[1:]
        with open(book_path, 'rb') as f:
            file_bytes = f.read()
        
        self.book_repository.save_book_file(book_id, file_bytes, suffix)

        current_max_chunk = max_chunk_chars if max_chunk_chars is not None else self.max_chunk_chars
        original_max_chunk = self.max_chunk_chars
        self.max_chunk_chars = current_max_chunk

        try:
            chunks = self._split_long_chapters(reader.chapters)
            logger.info(f"[{reader.title}] Split {len(reader.chapters)} chapters into {len(chunks)} sub-chapters (max={current_max_chunk} chars)")

            chunks = await classify_content_types(chunks, llm=None)

            self.book_repository.save_chunks(book_id, chunks)
            story_chunk_list = [ch for ch in chunks if ch.content_type == "story_content"]
            logger.info(f"[{reader.title}] AI classification: {len(story_chunk_list)}/{len(chunks)} story chapters")

            return {
                "book_id": book_id,
                "title": reader.title,
                "total_chunks_count": len(chunks),
                "story_chunks_count": len(story_chunk_list),
                "chunks": chunks,
                "story_chunks": story_chunk_list
            }
        finally:
            self.max_chunk_chars = original_max_chunk

    def create_book(self, user_id: str, title: str) -> Book:
        """创建书籍"""
        book_id = str(uuid.uuid4())
        nodes_file_path = f"data/books/{book_id}"
        book = Book(
            id=book_id,
            user_id=user_id,
            title=title,
            nodes_file_path=nodes_file_path,
            status="pending",
            is_deleted=False,
            created_at=datetime.now()
        )
        self.db.create_book(book)
        return book

    def get_book(self, book_id: str) -> Optional[Book]:
        return self.db.get_book(book_id)

    def get_books_for_user(self, user_id: str) -> List[Book]:
        return self.db.get_books_for_user(user_id)

    def update_book_status(self, book_id: str, status: str, message: str = None) -> Book:
        """更新书籍状态和消息"""
        self.db.update_book_status(book_id, status, message)
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        return book

    def delete_book(self, book_id: str) -> None:
        """软删除书籍"""
        self.db.soft_delete_book(book_id)

    def create_book_object(self, book_id: str, user_id: str, title: str, author: str | None, publisher: str | None, cover_url: str | None, nodes_file_path: str) -> Book:
        """创建书籍（带完整字段）"""
        book = Book(
            id=book_id,
            user_id=user_id,
            title=title,
            author=author,
            publisher=publisher,
            cover_url=cover_url,
            nodes_file_path=nodes_file_path,
            status="pending",
            is_deleted=False,
            created_at=datetime.now()
        )
        self.db.create_book(book)
        return book