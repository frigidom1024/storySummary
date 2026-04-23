import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.structure_builder import StructureBuilder
from src.models.narrative_node import NarrativeNode, CharacterState


class TestStructureBuilder:
    def test_creates_linear_mainline(self):
        """Test structure building with importance-based role inference."""
        nodes = [
            NarrativeNode(id="n-001", parent_chunk_id="c-0", beat_index=0,
                          scene="s1", importance=0.3, thread_id="main"),
            NarrativeNode(id="n-002", parent_chunk_id="c-0", beat_index=1,
                          scene="s2", importance=0.6, thread_id="main"),
            NarrativeNode(id="n-003", parent_chunk_id="c-0", beat_index=2,
                          scene="s3", importance=0.85, turning_point="重大转折", thread_id="main"),
            NarrativeNode(id="n-004", parent_chunk_id="c-0", beat_index=3,
                          scene="s4", importance=0.7, thread_id="main"),
        ]
        builder = StructureBuilder()
        structure = builder.build(nodes)

        assert structure.linear_mainline == ["n-001", "n-002", "n-003", "n-004"]
        # n-001: low importance, early -> opening
        # n-002: medium importance -> rising
        # n-003: high importance + turning_point -> climax
        # n-004: late position -> ending
        assert "n-001" in structure.opening
        assert "n-002" in structure.rising
        assert "n-003" in structure.climax
        assert "n-004" in structure.ending

    def test_infers_rising_by_default(self):
        """Test that medium importance nodes are labeled as rising."""
        nodes = [
            NarrativeNode(id="n-001", parent_chunk_id="c-0", beat_index=0,
                          scene="s1", importance=0.5, thread_id="main"),
            NarrativeNode(id="n-002", parent_chunk_id="c-0", beat_index=1,
                          scene="s2", importance=0.6, thread_id="main"),
            NarrativeNode(id="n-003", parent_chunk_id="c-0", beat_index=2,
                          scene="s3", importance=0.5, thread_id="main"),
        ]
        builder = StructureBuilder()
        structure = builder.build(nodes)

        # Middle nodes should be rising (n-001 at 0%, n-003 at 100% thresholds)
        assert "n-002" in structure.rising
