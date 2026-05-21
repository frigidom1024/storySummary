import pytest
import json
import tempfile
from pathlib import Path
from src.writing.state import WritingState, WritingPhase, PipelinePhase

def test_state_initialization():
    state = WritingState(book_title="Test Book")
    assert state.phase == WritingPhase.PLANNING
    assert state.current_chunk_index == 0
    assert len(state.written_chapters) == 0
    assert len(state.established_claims) == 0

def test_state_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "state.json"
        state = WritingState(book_title="Test Book")
        state.current_chunk_index = 2
        state.established_claims.append("克拉克是宇宙诗人")
        state.save(path)

        loaded = WritingState.load(path)
        assert loaded.current_chunk_index == 2
        assert "克拉克是宇宙诗人" in loaded.established_claims
        assert loaded.book_title == "Test Book"

def test_state_update_after_chapter():
    state = WritingState(book_title="Test")
    state.phase = WritingPhase.WRITING
    state.current_chunk_index = 0
    state.add_chapter("chunk-0001", "这是稿子...")
    state.current_chunk_index += 1  # caller responsibility
    assert len(state.written_chapters) == 1
    assert state.current_chunk_index == 1
