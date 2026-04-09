import sqlite3
import json
import uuid
from pathlib import Path
from src.models.narrative_node import NarrativeNode, CharacterState
from src.models.story_structure import StoryStructure


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=1) as conn:
            conn.execute("PRAGMA journal_mode=WAL")

            # books: each book's metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id)")

            # chunks: text chunks per book
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT NOT NULL,
                    book_id TEXT NOT NULL,
                    chapter_title TEXT,
                    text TEXT NOT NULL,
                    "order" INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (book_id, id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_book ON chunks(book_id)")

            # nodes: narrative nodes per book
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT NOT NULL,
                    book_id TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    beat_index INTEGER DEFAULT 0,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (book_id, id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_book ON nodes(book_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_chunk ON nodes(chunk_id)")

            # story_structures: structure per book
            conn.execute("""
                CREATE TABLE IF NOT EXISTS story_structures (
                    book_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)

    # === Books ===

    def save_book_metadata(self, book_id: str, user_id: str, title: str):
        """Save or update book metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO books (id, user_id, title, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (book_id, user_id, title))

    def get_books_for_user(self, user_id: str) -> list[dict]:
        """Get all books for a user."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM books WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [
                {"id": r[0], "user_id": r[1], "title": r[2], "created_at": r[3], "updated_at": r[4]}
                for r in rows
            ]

    def get_book(self, book_id: str) -> dict | None:
        """Get a single book by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, user_id, title, created_at, updated_at FROM books WHERE id = ?",
                (book_id,)
            ).fetchone()
            if row:
                return {"id": row[0], "user_id": row[1], "title": row[2], "created_at": row[3], "updated_at": row[4]}
            return None

    # === Nodes ===

    def save_node(self, node: NarrativeNode, book_id: str):
        """Save a narrative node for a specific book."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes (id, book_id, chunk_id, beat_index, data) VALUES (?, ?, ?, ?, ?)",
                (node.id, book_id, node.parent_chunk_id, node.beat_index, node.model_dump_json())
            )

    def get_node(self, node_id: str, book_id: str) -> NarrativeNode | None:
        """Get a single node by ID within a specific book."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM nodes WHERE id = ? AND book_id = ?",
                (node_id, book_id)
            ).fetchone()
            if row:
                return NarrativeNode.model_validate_json(row[0])
            return None

    def get_nodes_for_book(self, book_id: str) -> list[NarrativeNode]:
        """Get all narrative nodes for a specific book."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT data FROM nodes WHERE book_id = ? ORDER BY chunk_id, beat_index",
                (book_id,)
            ).fetchall()
            return [NarrativeNode.model_validate_json(row[0]) for row in rows]

    # === Chunks ===

    def save_chunk(self, book_id: str, chunk_id: str, text: str, chapter_title: str = None, order: int = 0):
        """Save a text chunk for a specific book."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chunks (id, book_id, chapter_title, text, \"order\") VALUES (?, ?, ?, ?, ?)",
                (chunk_id, book_id, chapter_title, text, order)
            )

    def get_chunks_for_book(self, book_id: str) -> list[dict]:
        """Get all chunks for a specific book, ordered by 'order'."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, chapter_title, text, \"order\" FROM chunks WHERE book_id = ? ORDER BY \"order\"",
                (book_id,)
            ).fetchall()
            return [
                {"id": r[0], "chapter_title": r[1], "text": r[2], "order": r[3]}
                for r in rows
            ]

    # === Structures ===

    def save_structure(self, book_id: str, structure: StoryStructure):
        """Save story structure for a specific book."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO story_structures (book_id, data) VALUES (?, ?)",
                (book_id, structure.model_dump_json())
            )

    def get_structure_for_book(self, book_id: str) -> StoryStructure | None:
        """Get story structure for a specific book."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM story_structures WHERE book_id = ?",
                (book_id,)
            ).fetchone()
            if row:
                return StoryStructure.model_validate_json(row[0])
            return None

    # Backward compatibility alias
    def get_structure(self, book_id: str) -> StoryStructure | None:
        return self.get_structure_for_book(book_id)