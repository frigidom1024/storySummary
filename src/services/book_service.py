import uuid
from datetime import datetime
from typing import List, Optional
from src.models.book import Book
from src.services.interfaces import IBookService
from src.storage.database import Database
from src.storage.path_builder import PathBuilder


class BookService(IBookService):
    def __init__(self, db: Database, path_builder: PathBuilder):
        self.db = db
        self.path_builder = path_builder

    def create_book(self, user_id: str, title: str) -> Book:
        """创建书籍"""
        book_id = str(uuid.uuid4())
        nodes_file_path = self.path_builder.build_nodes_file(user_id, book_id)
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

    def update_book_status(self, book_id: str, status: str) -> Book:
        """更新书籍状态"""
        self.db.update_book_status(book_id, status)
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        return book

    def delete_book(self, book_id: str) -> None:
        """软删除书籍"""
        self.db.soft_delete_book(book_id)