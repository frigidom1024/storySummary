import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import AIMessage
from src.models.chunk import Chunk
from src.analysis.node_generator import NarrativeNodeGenerator
from src.analysis.agents.agent1_extractor import Agent1Extractor, NarrativeBeatModel, CharacterStateModel
from src.models.narrative_node import NarrativeNode, CharacterState, RelationshipStateChange


class TestNarrativeNodeGenerator:
    @pytest.mark.asyncio
    async def test_generates_multiple_beats_from_chunk(self):
        """One chunk → multiple narrative beats (multi-beat extraction)."""
        generator = NarrativeNodeGenerator(api_key="test-key")
        chunk = Chunk(id="c-001", text="John walked in. He was scared. Then he saw something.", order=0)

        # Mock the generate_from_chunk method directly
        with patch.object(generator, 'generate_from_chunk', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = [
                NarrativeNode(
                    id="n-0-0",
                    parent_chunk_id="c-001",
                    beat_index=0,
                    scene="A room",
                    location="A room",
                    scene_timing="morning",
                    characters=[CharacterState(name="John", state_before="calm")],
                    situation="John enters an empty room",
                    turning_point="John notices something unusual",
                    emotional_arc="John从好奇变为警觉",
                    mood_tone="平静, 略带紧张",
                    narrative_rhythm="slow",
                    discussion_prompts=[],
                    relationship_delta=[],
                    narrative_role="opening"
                ),
                NarrativeNode(
                    id="n-0-1",
                    parent_chunk_id="c-001",
                    beat_index=1,
                    scene="A room",
                    location="A room",
                    scene_timing="morning",
                    characters=[CharacterState(name="John", state_before="scared")],
                    situation="John confronts the unexpected sight",
                    turning_point="John sees something shocking",
                    emotional_arc="John从警觉变为恐惧",
                    mood_tone="紧张, 恐惧",
                    narrative_rhythm="fast",
                    discussion_prompts=["为什么John会感到恐惧？"],
                    relationship_delta=[],
                    narrative_role="rising"
                )
            ]
            nodes = await generator.generate_from_chunk(chunk)

        assert isinstance(nodes, list)
        assert len(nodes) == 2
        assert nodes[0].id == "n-0-0"
        assert nodes[1].id == "n-0-1"
        assert nodes[0].parent_chunk_id == "c-001"
        assert nodes[1].beat_index == 1
        assert nodes[0].characters[0].name == "John"
        assert nodes[1].characters[0].state_before == "scared"
        assert nodes[1].situation == "John confronts the unexpected sight"

    @pytest.mark.asyncio
    async def test_single_beat_still_returns_list(self):
        """Even a single beat returns a list for consistent handling."""
        generator = NarrativeNodeGenerator(api_key="test-key")
        chunk = Chunk(id="c-002", text="Simple sentence.", order=1)

        with patch.object(generator, 'generate_from_chunk', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = [
                NarrativeNode(
                    id="n-1-0",
                    parent_chunk_id="c-002",
                    beat_index=0,
                    scene="A place",
                    location="A place",
                    scene_timing="day",
                    characters=[],
                    situation="Something happens",
                    turning_point="Nothing significant",
                    emotional_arc="",
                    mood_tone="neutral",
                    narrative_rhythm="steady",
                    discussion_prompts=[],
                    relationship_delta=[],
                    narrative_role="opening"
                )
            ]
            nodes = await generator.generate_from_chunk(chunk)

        assert isinstance(nodes, list)
        assert len(nodes) == 1

    def test_validate_beat_normalizes_importance(self):
        agent1 = Agent1Extractor(api_key="test-key")
        beat = {"id": "n-0-0", "beat_index": 0, "scene": "场景", "importance": "2"}
        validated = agent1._validate_beat(beat)
        assert validated["importance"] == 1.0

    def test_validate_beat_has_interactions_default(self):
        agent1 = Agent1Extractor(api_key="test-key")
        beat = {"id": "n-0-0", "beat_index": 0, "scene": "场景"}
        validated = agent1._validate_beat(beat)
        assert validated["interactions"] == []


if __name__ == "__main__":
    import asyncio
    import json
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from dotenv import load_dotenv
    load_dotenv()

    from src.analysis.node_generator import NarrativeNodeGenerator
    from src.utils.reader.text import AdaptiveChunker

    async def test_wind():
        generator = NarrativeNodeGenerator()
        chunker = AdaptiveChunker()

        wind_path = Path(__file__).parent.parent.parent / 'samples' / 'wind.txt'
        with open(wind_path, 'r', encoding='utf-8') as f:
            text = f.read()

        chunks = chunker.chunk(text)
        print(f"Wind sample: {len(chunks)} chunks")

        all_results = []
        for i, chunk in enumerate(chunks[:2]):
            print(f"\nProcessing chunk {i}: chapter={chunk.chapter}, text len={len(chunk.text)}")
            nodes = await generator.generate_from_chunk(chunk)
            print(f"Generated {len(nodes)} nodes")

            for node in nodes:
                node_dict = {
                    "id": node.id,
                    "parent_chunk_id": node.parent_chunk_id,
                    "beat_index": node.beat_index,
                    "scene": node.scene,
                    "location": node.location,
                    "scene_timing": node.scene_timing,
                    "characters": [{"name": c.name, "state_before": c.state_before} for c in node.characters],
                    "situation": node.situation,
                    "turning_point": node.turning_point,
                    "importance": node.importance,
                    "emotional_arc": node.emotional_arc,
                    "mood_tone": node.mood_tone,
                    "discussion_prompts": node.discussion_prompts,
                    "relationship_delta": [{"pair": r.pair, "from": r.from_state, "to": r.to_state} for r in node.relationship_delta],
                    "time_label": node.time_label,
                    "thread_id": node.thread_id,
                    "thread_name": node.thread_name,
                }
                all_results.append(node_dict)

        # Save to file
        output_path = Path(__file__).parent.parent.parent / 'node_output.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(all_results)} nodes to {output_path}")

    asyncio.run(test_wind())