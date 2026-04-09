import logging
from pathlib import Path
from src.core.chunker import ChapterChunker
from src.core.node_generator import NarrativeNodeGenerator
from src.core.structure_builder import StructureBuilder
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
        self.db = Database(db_path)
        self.vector_store = VectorStore(vector_store_path)
        self.title = None

    async def process_file(self, book_path: str) -> dict:
        """Process a book file (EPUB or PDF) through the pipeline."""
        from src.utils.book_adapter import read_book
        reader = read_book(book_path)
        return await self.process(reader.read(), reader.title)

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

    async def run_writing_agent(self, chunks: list[Chunk], nodes: list[NarrativeNode], title: str):
        """Run the podcast writing agent after nodes are generated."""
        from src.generation.podcast_writing_agent import PodcastWritingAgent
        agent = PodcastWritingAgent(
            api_key=self.api_key,
            model=self.model,
        )
        return await agent.run(chunks, nodes, title)

    async def process_full(self, book_path: str):
        """Run the full pipeline: book → chunks → nodes → podcast manuscript."""
        from src.utils.book_adapter import read_book

        reader = read_book(book_path)
        text = reader.read()

        # Existing: chunk + generate nodes
        chunks = self.chunker.chunk(text)
        all_nodes = []
        for chunk in chunks:
            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]
            all_nodes.extend(nodes)

        # New: write podcast manuscript
        manuscript = await self.run_writing_agent(chunks, all_nodes, reader.title)

        return manuscript
