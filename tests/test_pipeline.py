import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import shutil
import os
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from src.pipeline import NovelToPodcastPipeline
from src.models.narrative_node import NarrativeNode, CharacterState, RelationshipStateChange


class TestPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_multi_beat(self):
        # Use temp directories for ChromaDB (doesn't support :memory: for PersistentClient)
        temp_dir = tempfile.mkdtemp()
        db_path = tempfile.mktemp(suffix='.db')
        vector_store_path = temp_dir

        try:
            pipeline = NovelToPodcastPipeline(
                db_path=db_path,
                vector_store_path=vector_store_path,
                api_key="test-key"
            )

            novel_text = """
            Chapter 1

            John walked into the dark room. His heart pounded. Then he heard a noise.
            """

            # Pre-built mock nodes for multi-beat response
            mock_nodes = [
                NarrativeNode(
                    id="n-0001-0",
                    parent_chunk_id="chunk-0000",
                    beat_index=0,
                    scene="A dark room",
                    location="A dark room",
                    scene_timing="night",
                    characters=[CharacterState(name="John", state_before="scared")],
                    situation="John is alone in a dark room",
                    turning_point="John enters the dark room",
                    emotional_arc="John从平静变为警觉",
                    mood_tone="紧张, 恐惧",
                    narrative_rhythm="slow",
                    discussion_prompts=[],
                    relationship_delta=[],
                    narrative_role="opening"
                ),
                NarrativeNode(
                    id="n-0001-1",
                    parent_chunk_id="chunk-0000",
                    beat_index=1,
                    scene="A dark room",
                    location="A dark room",
                    scene_timing="night",
                    characters=[CharacterState(name="John", state_before="terrified")],
                    situation="John hears an unexpected noise",
                    turning_point="John hears a noise in the darkness",
                    emotional_arc="John从警觉变为恐惧",
                    mood_tone="恐惧, 紧张",
                    narrative_rhythm="fast",
                    discussion_prompts=["这个声音意味着什么？"],
                    relationship_delta=[],
                    narrative_role="rising"
                )
            ]

            # Mock the node_generator's generate_from_chunk method
            with patch.object(pipeline.node_generator, 'generate_from_chunk', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = mock_nodes
                result = await pipeline.process(novel_text, title="Test Story")

            # Should have 2 nodes from 1 chunk (multi-beat)
            assert len(result["nodes"]) == 2
            assert result["nodes"][0].prev_node_id == ""
            assert result["nodes"][1].prev_node_id == "n-0001-0"
            assert result["structure"] is not None
        finally:
            # Clean up - close db connection first on Windows
            pipeline.db = None
            shutil.rmtree(temp_dir, ignore_errors=True)
            if os.path.exists(db_path):
                try:
                    os.unlink(db_path)
                except PermissionError:
                    pass  # Windows file locking issue, ignore


if __name__ == "__main__":
    import asyncio
    import json
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv()

    import tempfile
    import shutil

    async def test_wind_sample():
        temp_dir = tempfile.mkdtemp()
        db_path = tempfile.mktemp(suffix='.db')
        vector_store_path = temp_dir

        try:
            pipeline = NovelToPodcastPipeline(
                db_path=db_path,
                vector_store_path=vector_store_path,
                api_key=None  # Will use env vars
            )

            # Load wind sample
            wind_path = Path(__file__).parent.parent / 'samples' / 'wind.txt'
            with open(wind_path, 'r', encoding='utf-8') as f:
                text = f.read()

            print("=" * 60)
            print("PIPELINE TEST WITH WIND SAMPLE")
            print("=" * 60)
            print(f"Text length: {len(text)} characters")

            result = await pipeline.process(text, title="秋风辞")

            print(f"\nPipeline Results:")
            print(f"  Title: {result['title']}")
            print(f"  Total nodes: {len(result['nodes'])}")
            print(f"  Structure - opening: {len(result['structure'].opening)}, rising: {len(result['structure'].rising)}, climax: {len(result['structure'].climax)}, ending: {len(result['structure'].ending)}")

            # Save results
            output_path = Path(__file__).parent.parent / 'pipeline_output.json'
            nodes_output = []
            for node in result['nodes']:
                nodes_output.append({
                    "id": node.id,
                    "parent_chunk_id": node.parent_chunk_id,
                    "beat_index": node.beat_index,
                    "scene": node.scene,
                    "characters": [{"name": c.name, "state_before": c.state_before} for c in node.characters],
                    "situation": node.situation,
                    "turning_point": node.turning_point,
                    "emotional_arc": node.emotional_arc,
                    "mood_tone": node.mood_tone,
                    "narrative_rhythm": node.narrative_rhythm,
                    "discussion_prompts": node.discussion_prompts,
                    "relationship_delta": [{"pair": r.pair, "from": r.from_state, "to": r.to_state} for r in node.relationship_delta],
                    "narrative_role": node.narrative_role,
                    "prev_node_id": node.prev_node_id
                })

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "title": result['title'],
                    "nodes": nodes_output,
                    "structure": {
                        "opening": result['structure'].opening,
                        "rising": result['structure'].rising,
                        "climax": result['structure'].climax,
                        "ending": result['structure'].ending
                    }
                }, f, ensure_ascii=False, indent=2)
            print(f"\nSaved to {output_path}")

            # Print first few nodes
            print("\n" + "=" * 60)
            print("FIRST 3 NODES:")
            print("=" * 60)
            for node in result['nodes'][:3]:
                print(f"\n[{node.id}] {node.scene}")
                print(f"  Characters: {[c.name for c in node.characters]}")
                print(f"  Situation: {node.situation[:80]}...")
                print(f"  Role: {node.narrative_role}")

        finally:
            pipeline.db = None
            shutil.rmtree(temp_dir, ignore_errors=True)
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except PermissionError:
                pass

    asyncio.run(test_wind_sample())
