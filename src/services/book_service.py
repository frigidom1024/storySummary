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
    def __init__(self, db: Database = None, base_dir: str = "data"):
        if db is None:
            db = Database()
        self.db = db
        self.book_repository = BookRepository(base_dir=base_dir)

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

    async def process_file(self, book_path: str, user_id: str = "default-user") -> dict:
        """Process a book file (EPUB or PDF) through the pipeline."""
        reader = read_book(book_path)

        book_id = self._ensure_book(user_id, reader.title)

        suffix = Path(book_path).suffix.lower()[1:]
        with open(book_path, 'rb') as f:
            file_bytes = f.read()
        
        self.book_repository.save_book_file(book_id, file_bytes, suffix)

        chunks = await classify_content_types(reader.chapters, llm=None)

        self.book_repository.save_chunks(book_id, chunks)
        story_chunks = [ch for ch in chunks if ch.content_type == "story_content"]
        logger.info(f"[{reader.title}] AI classification: {len(story_chunks)}/{len(chunks)} story chapters")

        return {
            "book_id": book_id,
            "title": reader.title,
            "total_chunks": len(chunks),
            "story_chunks": len(story_chunks),
            "chunks": chunks
        }

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