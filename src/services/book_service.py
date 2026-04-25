import uuid
from datetime import datetime
from typing import List, Optional
from src.models.book import Book
from src.services.interfaces import IBookService
from src.storage.database import Database


class BookService(IBookService):
    def __init__(self, db: Database):
        self.db = db

    def create_book(self, user_id: str, title: str) -> Book:
        """创建书籍"""
        book_id = str(uuid.uuid4())
        nodes_file_path = f"data/books/{book_id}"  # BookStorage 内部管理路径
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