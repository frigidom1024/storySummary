import pytest
import json
import tempfile
from pathlib import Path
from src.generation.podcast_writing_agent import PodcastWritingAgent
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState

def make_nodes(chunk_id: str, count: int) -> list[NarrativeNode]:
    return [
        NarrativeNode(
            id=f"{chunk_id}-n{i}",
            parent_chunk_id=chunk_id,
            beat_index=i,
            scene=f"场景{i}",
            situation=f"情境{i}",
            turning_point=f"转折{i}",
            emotional_arc=f"情绪{i}",
            mood_tone="平静",
            narrative_rhythm="steady",
            narrative_role="rising"
        )
        for i in range(count)
    ]


def test_agent_init():
    agent = PodcastWritingAgent(api_key="test-key")
    assert agent.state is None
    assert agent.plan is None


def test_build_nodes_summary():
    """Test that _build_nodes_summary formats NarrativeNodes correctly."""
    agent = PodcastWritingAgent(api_key="test-key")
    nodes = make_nodes("chunk-0001", 2)
    summary = agent._build_nodes_summary(nodes)
    assert "场景0" in summary
    assert "情境0" in summary
    assert "转折0" in summary


def test_state_path_generation():
    """Test output path for state file."""
    agent = PodcastWritingAgent(api_key="test-key")
    path = agent._get_state_path("神的九十亿个名字")
    assert "神的九十亿个名字" in str(path)
    assert path.name == "writing_state.json"
