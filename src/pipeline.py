from pathlib import Path
from src.core.chunker import ChapterChunker
from src.core.node_generator import NarrativeNodeGenerator
from src.core.structure_builder import StructureBuilder
from src.core.state_tracker import StateTracker
from src.storage.database import Database
from src.storage.vector_store import VectorStore
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.models.chunk import Chunk


class NovelToPodcastPipeline:
    def __init__(
        self,
        db_path: str,
        vector_store_path: str,
        api_key: str = None,
        model: str = None
    ):
        self.api_key = api_key
        self.model = model
        self.chunker = ChapterChunker()
        self.node_generator = NarrativeNodeGenerator(api_key=api_key, model=model)
        self.structure_builder = StructureBuilder()
        self.state_tracker = StateTracker()
        self.db = Database(db_path)
        self.vector_store = VectorStore(vector_store_path)

    async def process(self, novel_text: str, title: str) -> dict:
        # 1. Chunk the novel
        chunks = self.chunker.chunk(novel_text)

        # 2. Generate MULTIPLE narrative nodes per chunk (multi-beat)
        all_nodes = []
        for chunk in chunks:
            # Each chunk can produce multiple nodes (beats)
            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]

            # Link nodes and track state
            prev_node = all_nodes[-1] if all_nodes else None

            for i, node in enumerate(nodes):
                node.prev_node_id = prev_node.id if prev_node else ""

                # Calculate state delta
                if prev_node:
                    node.state_delta = self.state_tracker.track(prev_node, node)

                # Save to storage
                self.db.save_node(node)
                self.db.save_chunk(title, chunk.id, chunk.text)
                self.vector_store.add_node(node, chunk.text)

                prev_node = node
                all_nodes.append(node)

        # 3. Build story structure
        structure = self.structure_builder.build(all_nodes)

        # 4. Save structure
        self.db.save_structure(title, structure)

        return {
            "title": title,
            "nodes": all_nodes,
            "structure": structure
        }