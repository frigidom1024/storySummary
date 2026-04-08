import pytest
import tempfile
import os
import gc
from src.storage.database import Database
from src.models.narrative_node import NarrativeNode, CharacterState


class TestDatabase:
    def test_save_and_retrieve_node(self):
        tmpdir = tempfile.mkdtemp()
        try:
            db = Database(os.path.join(tmpdir, "test.db"))
            node = NarrativeNode(
                id="n-001",
                scene="A dark room",
                characters=[CharacterState(name="John", state="scared", goal="escape")],
                event="John entered the dark room",
                tension="Unknown danger",
                stakes="Life or death",
                narrative_role="opening"
            )
            db.save_node(node)
            retrieved = db.get_node("n-001")

            assert retrieved is not None
            assert retrieved.id == "n-001"
            assert retrieved.scene == "A dark room"
            assert len(retrieved.characters) == 1
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass

    def test_save_and_retrieve_structure(self):
        tmpdir = tempfile.mkdtemp()
        try:
            from src.models.story_structure import StoryStructure
            db = Database(os.path.join(tmpdir, "test.db"))
            structure = StoryStructure(
                linear_mainline=["n-001", "n-002"],
                opening=["n-001"],
                rising=["n-002"]
            )
            db.save_structure("story-1", structure)
            retrieved = db.get_structure("story-1")

            assert retrieved is not None
            assert retrieved.linear_mainline == ["n-001", "n-002"]
        finally:
            del db
            gc.collect()
            try:
                os.unlink(os.path.join(tmpdir, "test.db"))
            except PermissionError:
                pass