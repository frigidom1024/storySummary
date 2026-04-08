import logging
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
from src.logging_config import logger


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
        self.title = None

    async def process(self, novel_text: str, title: str) -> dict:
        self.title = title
        logger.info(f"[{title}] Starting pipeline...")

        # 1. Chunk the novel
        logger.info(f"[{title}] Chunking novel...")
        chunks = self.chunker.chunk(novel_text)
        logger.info(f"[{title}] Generated {len(chunks)} chunks")

        # 2. Generate MULTIPLE narrative nodes per chunk (multi-beat)
        all_nodes = []
        total_beats = 0
        for i, chunk in enumerate(chunks):
            logger.debug(f"[{title}] Processing chunk {i+1}/{len(chunks)}: {chunk.chapter or 'No chapter'}")
            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]

            total_beats += len(nodes)
            logger.info(f"[{title}] Chunk {i+1}: {len(nodes)} beats generated")

            # Link nodes and track state
            prev_node = all_nodes[-1] if all_nodes else None

            for j, node in enumerate(nodes):
                node.prev_node_id = prev_node.id if prev_node else ""

                # Calculate state delta
                if prev_node:
                    node.state_delta = self.state_tracker.track(prev_node, node)
                    logger.debug(f"[{title}] Node {node.id}: state delta = {node.state_delta[:50]}...")

                # Save to storage
                self.db.save_node(node)
                self.db.save_chunk(title, chunk.id, chunk.text)
                self.vector_store.add_node(node, chunk.text)

                prev_node = node
                all_nodes.append(node)

        logger.info(f"[{title}] Total: {total_beats} narrative nodes generated")

        # 3. Build story structure
        logger.info(f"[{title}] Building story structure...")
        structure = self.structure_builder.build(all_nodes)
        logger.info(f"[{title}] Structure: opening={len(structure.opening)}, rising={len(structure.rising)}, climax={len(structure.climax)}, ending={len(structure.ending)}")

        # 4. Save structure
        self.db.save_structure(title, structure)
        logger.info(f"[{title}] Pipeline complete!")

        return {
            "title": title,
            "nodes": all_nodes,
            "structure": structure
        }
