import sqlite3
import json
from pathlib import Path
from src.models.narrative_node import NarrativeNode, CharacterState
from src.models.story_structure import StoryStructure


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS structures (
                    story_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    story_id TEXT,
                    data TEXT NOT NULL
                )
            """)

    def save_node(self, node: NarrativeNode):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nodes (id, data) VALUES (?, ?)",
                (node.id, node.model_dump_json())
            )

    def get_node(self, node_id: str) -> NarrativeNode | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
            if row:
                return NarrativeNode.model_validate_json(row[0])
            return None

    def save_structure(self, story_id: str, structure: StoryStructure):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO structures (story_id, data) VALUES (?, ?)",
                (story_id, structure.model_dump_json())
            )

    def get_structure(self, story_id: str) -> StoryStructure | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM structures WHERE story_id = ?", (story_id,)
            ).fetchone()
            if row:
                return StoryStructure.model_validate_json(row[0])
            return None

    def save_chunk(self, story_id: str, chunk_id: str, text: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chunks (id, story_id, data) VALUES (?, ?, ?)",
                (chunk_id, story_id, json.dumps({"text": text}))
            )