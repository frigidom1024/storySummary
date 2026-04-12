import sqlite3
from typing import List, Optional
from src.models.user import User
from src.models.book import Book


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=1) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            # users 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    profile TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # books 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    nodes_file_path TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    is_deleted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id)")

            # 迁移：添加新列（幂等）
            for col, dtype in [("author", "TEXT"), ("publisher", "TEXT"), ("cover_url", "TEXT")]:
                try:
                    conn.execute(f"ALTER TABLE books ADD COLUMN {col} {dtype}")
                except sqlite3.OperationalError:
                    pass  # 列已存在

            # 迁移：确保 nodes_file_path 列存在
            try:
                conn.execute("ALTER TABLE books ADD COLUMN nodes_file_path TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # 列已存在

    # === Users ===

    def create_user(self, user: User) -> None:
        """创建用户"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO users (id, username, email, password_hash, profile, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user.id, user.username, user.email, user.password_hash,
                 str(user.profile), user.created_at)
            )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据 ID 获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash, profile, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            if row:
                import json
                return User(
                    id=row[0], username=row[1], email=row[2],
                    password_hash=row[3], profile=json.loads(row[4]), created_at=row[5]
                )
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash, profile, created_at FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            if row:
                import json
                return User(
                    id=row[0], username=row[1], email=row[2],
                    password_hash=row[3], profile=json.loads(row[4]), created_at=row[5]
                )
            return None

    def update_user_profile(self, user_id: str, profile: dict) -> None:
        """更新用户资料"""
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET profile = ? WHERE id = ?",
                (json.dumps(profile), user_id)
            )

    # === Books ===

    def create_book(self, book: Book) -> None:
        """创建书籍"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO books (id, user_id, title, author, publisher, cover_url, nodes_file_path, status, is_deleted, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (book.id, book.user_id, book.title, book.author, book.publisher,
                 book.cover_url, book.nodes_file_path, book.status, int(book.is_deleted), book.created_at)
            )

    def get_book(self, book_id: str) -> Optional[Book]:
        """获取书籍"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT id, user_id, title, author, publisher, cover_url, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE id = ? AND is_deleted = 0""",
                (book_id,)
            ).fetchone()
            if row:
                return Book(
                    id=row[0], user_id=row[1], title=row[2],
                    author=row[3], publisher=row[4], cover_url=row[5],
                    nodes_file_path=row[6], status=row[7],
                    is_deleted=bool(row[8]), created_at=row[9]
                )
            return None

    def get_books_for_user(self, user_id: str) -> List[Book]:
        """获取用户的所有书籍"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT id, user_id, title, author, publisher, cover_url, nodes_file_path, status, is_deleted, created_at
                   FROM books WHERE user_id = ? AND is_deleted = 0 ORDER BY created_at DESC""",
                (user_id,)
            ).fetchall()
            return [
                Book(
                    id=r[0], user_id=r[1], title=r[2],
                    author=r[3], publisher=r[4], cover_url=r[5],
                    nodes_file_path=r[6], status=r[7],
                    is_deleted=bool(r[8]), created_at=r[9]
                )
                for r in rows
            ]

    def update_book_status(self, book_id: str, status: str) -> None:
        """更新书籍状态"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE books SET status = ? WHERE id = ?",
                (status, book_id)
            )

    def soft_delete_book(self, book_id: str) -> None:
        """软删除书籍"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE books SET is_deleted = 1 WHERE id = ?",
                (book_id,)
            )