import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import os
import gc
from src.storage.database import Database
from src.storage.vector_store import VectorStore
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


class TestVectorStore:
    def test_add_and_search_node(self):
        tmpdir = tempfile.mkdtemp()
        try:
            vs = VectorStore(tmpdir)
            node = NarrativeNode(
                id="n-001",
                scene="旧书店，下午",
                characters=[CharacterState(name="陈屿", state="无聊", goal="消磨时间")],
                event="陈屿在旧书店里蹲了两个小时，膝盖发僵",
                tension="家庭压力与个人现状的冲突",
                stakes="个人精神状态",
                narrative_role="opening"
            )
            original_text = "八月底的南京，梧桐叶子还绿着，但阳光已经不那么烫人了。陈屿在青岛路上的一家旧书店里蹲了快两个小时，膝盖酸得发僵。"

            # Add node
            vs.add_node(node, original_text)

            # Search
            results = vs.search("旧书店 陈屿", n_results=1)

            assert results is not None
            assert len(results['ids'][0]) == 1
            assert results['ids'][0][0] == "n-001"
        finally:
            del vs
            gc.collect()


if __name__ == "__main__":
    import shutil
    # Test with wind sample
    wind_path = Path(__file__).parent.parent.parent / 'node_output.json'
    if not wind_path.exists():
        print("node_output.json not found. Run node_generator test first.")
        exit(1)

    import json
    with open(wind_path, 'r', encoding='utf-8') as f:
        nodes_data = json.load(f)

    tmpdir = tempfile.mkdtemp()
    vs = VectorStore(tmpdir)

    # Load original text
    original_path = Path(__file__).parent.parent.parent / 'samples' / 'wind'
    with open(original_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # Add nodes
    print("Adding nodes to vector store...")
    for d in nodes_data:
        chars = [CharacterState(name=c['name'], state=c.get('state', ''), goal=c.get('goal', '')) for c in d.get('characters', [])]
        node = NarrativeNode(
            id=d['id'],
            parent_chunk_id=d.get('parent_chunk_id', ''),
            beat_index=d.get('beat_index', 0),
            scene=d['scene'],
            characters=chars,
            event=d['event'],
            dialogue_summary=d.get('dialogue_summary', ''),
            tension=d.get('tension', ''),
            stakes=d.get('stakes', ''),
            foreshadow=d.get('foreshadow', ''),
            narrative_role=d.get('narrative_role', '')
        )
        vs.add_node(node, full_text)

    print(f"Added {len(nodes_data)} nodes")

    # Test search
    queries = [
        "旧书店 陈屿",
        "沈昭 短信",
        "方远 林知夏"
    ]

    print("\n" + "=" * 60)
    print("VECTOR SEARCH TEST")
    print("=" * 60)

    for query in queries:
        print(f"\nQuery: {query}")
        results = vs.search(query, n_results=2)
        for i, (doc_id, doc, meta) in enumerate(zip(
            results['ids'][0],
            results['documents'][0],
            results['metadatas'][0]
        )):
            print(f"  [{i+1}] {doc_id}")
            print(f"      Scene: {meta['scene']}")
            print(f"      Event: {meta['event'][:60]}...")

    # Save results
    output_path = Path(__file__).parent.parent.parent / 'vector_search_output.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Vector Search Test Results\n")
        f.write("=" * 60 + "\n\n")
        for query in queries:
            f.write(f"Query: {query}\n")
            results = vs.search(query, n_results=2)
            for i, (doc_id, doc, meta) in enumerate(zip(
                results['ids'][0],
                results['documents'][0],
                results['metadatas'][0]
            )):
                f.write(f"  [{i+1}] {doc_id}\n")
                f.write(f"      Scene: {meta['scene']}\n")
                f.write(f"      Event: {meta['event']}\n\n")
    print(f"\nSaved to {output_path}")

    # Cleanup
    del vs
    gc.collect()
    shutil.rmtree(tmpdir, ignore_errors=True)

