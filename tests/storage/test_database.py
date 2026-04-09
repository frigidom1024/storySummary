import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import os
import gc
import uuid
from src.storage.database import Database
from src.models.narrative_node import NarrativeNode, CharacterState


class TestDatabase:
    def test_save_and_retrieve_node_with_book_id(self):
        """Nodes from different books with same node_id must not collide."""
        tmpdir = tempfile.mkdtemp()
        book1 = str(uuid.uuid4())
        book2 = str(uuid.uuid4())
        try:
            db = Database(os.path.join(tmpdir, "test.db"))

            # Save node for book1
            node1 = NarrativeNode(
                id="n-001",
                parent_chunk_id="c-001",
                beat_index=0,
                scene="咖啡馆",
                situation="林夏在等陈远",
                turning_point="收到短信",
                emotional_arc="林夏从期待到犹豫",
                mood_tone="紧张",
                narrative_rhythm="steady",
                narrative_role="rising",
            )
            db.save_node(node1, book1)

            # Save node for book2 with SAME id
            node2 = NarrativeNode(
                id="n-001",
                parent_chunk_id="c-001",
                beat_index=0,
                scene="办公室",
                situation="陈远在工作",
                turning_point="被叫去开会",
                emotional_arc="陈远从平静到紧张",
                mood_tone="压抑",
                narrative_rhythm="fast",
                narrative_role="rising",
            )
            db.save_node(node2, book2)

            # Retrieve should get correct node per book
            retrieved1 = db.get_node("n-001", book1)
            retrieved2 = db.get_node("n-001", book2)

            assert retrieved1 is not None
            assert retrieved2 is not None
            assert retrieved1.scene == "咖啡馆"  # book1
            assert retrieved2.scene == "办公室"   # book2
            assert retrieved1.id == retrieved2.id  # same id, different book
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass

    def test_save_and_retrieve_chunks_for_book(self):
        tmpdir = tempfile.mkdtemp()
        book_id = str(uuid.uuid4())
        try:
            db = Database(os.path.join(tmpdir, "test.db"))

            db.save_chunk(book_id, "chunk-001", "第一章内容")
            db.save_chunk(book_id, "chunk-002", "第二章内容")

            chunks = db.get_chunks_for_book(book_id)
            assert len(chunks) == 2
            texts = [c["text"] for c in chunks]
            assert "第一章内容" in texts
            assert "第二章内容" in texts
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass

    def test_cross_book_isolation_chunks(self):
        """Chunks from different books must not mix."""
        tmpdir = tempfile.mkdtemp()
        book1 = str(uuid.uuid4())
        book2 = str(uuid.uuid4())
        try:
            db = Database(os.path.join(tmpdir, "test.db"))

            db.save_chunk(book1, "chunk-001", "Book1 第一章")
            db.save_chunk(book2, "chunk-001", "Book2 第一章")

            chunks1 = db.get_chunks_for_book(book1)
            chunks2 = db.get_chunks_for_book(book2)

            assert len(chunks1) == 1
            assert len(chunks2) == 1
            assert chunks1[0]["text"] == "Book1 第一章"
            assert chunks2[0]["text"] == "Book2 第一章"
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass

    def test_save_and_retrieve_structure_for_book(self):
        """Structure should be isolated per book."""
        from src.models.story_structure import StoryStructure
        tmpdir = tempfile.mkdtemp()
        book1 = str(uuid.uuid4())
        book2 = str(uuid.uuid4())
        try:
            db = Database(os.path.join(tmpdir, "test.db"))

            s1 = StoryStructure(opening=["n1"], rising=["n2"], climax=["n3"], ending=[])
            s2 = StoryStructure(opening=["n1b"], rising=["n2b"], climax=[], ending=[])

            db.save_structure(book1, s1)
            db.save_structure(book2, s2)

            r1 = db.get_structure_for_book(book1)
            r2 = db.get_structure_for_book(book2)

            assert r1 is not None
            assert r2 is not None
            assert r1.opening == ["n1"]
            assert r2.opening == ["n1b"]
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass

    def test_save_book_metadata(self):
        tmpdir = tempfile.mkdtemp()
        book_id = str(uuid.uuid4())
        try:
            db = Database(os.path.join(tmpdir, "test.db"))
            db.save_book_metadata(book_id, "user-123", "测试书名")

            books = db.get_books_for_user("user-123")
            assert len(books) == 1
            assert books[0]["title"] == "测试书名"
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass