import logging
import uuid
from pathlib import Path
from src.core.chunker import chunk_by_book_id
from src.core.node_generator import NarrativeNodeGenerator
from src.core.structure_builder import StructureBuilder
from src.storage.database import Database
from src.storage.vector_store import VectorStore
from src.storage.book_storage import BookStorage
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
        model: str = None,
        user_id: str = None,
    ):
        self.api_key = api_key
        self.model = model
        self.user_id = user_id or "default-user"
        self.node_generator = NarrativeNodeGenerator(api_key=api_key, model=model)
        self.structure_builder = StructureBuilder()
        self.db = Database(db_path)
        self.vector_store = VectorStore(vector_store_path)
        self.book_storage = BookStorage()
        self.title = None
        self.book_id = None

    def _ensure_book(self, title: str) -> str:
        """Ensure a book record exists, return book_id."""
        if self.book_id is None:
            # Check if book with this title exists for this user
            books = self.db.get_books_for_user(self.user_id)
            for b in books:
                if b.title == title:
                    self.book_id = b.id
                    break
            else:
                # Create new book
                from src.models.book import Book
                from datetime import datetime
                self.book_id = str(uuid.uuid4())
                book = Book(
                    id=self.book_id,
                    user_id=self.user_id,
                    title=title,
                    author="",
                    publisher="",
                    cover_url="",
                    nodes_file_path=f"data/books/{self.book_id}/nodes.json",
                    status="processing",
                    message="",
                    is_deleted=False,
                    created_at=datetime.now(),
                )
                self.db.create_book(book)
                # Create book directory
                book_dir = Path(f"data/books/{self.book_id}")
                book_dir.mkdir(parents=True, exist_ok=True)
        return self.book_id

    async def process_file(self, book_path: str) -> dict:
        """Process a book file (EPUB or PDF) through the pipeline."""
        from src.utils.reader import read_book
        import shutil

        reader = read_book(book_path)

        # Create book_id and save file to books directory
        book_id = self._ensure_book(reader.title)
        book_dir = Path(f"data/books/{book_id}")
        book_dir.mkdir(parents=True, exist_ok=True)

        # Copy file to books directory
        suffix = Path(book_path).suffix.lower()
        dest_path = book_dir / f"book{suffix}"
        shutil.copy2(book_path, dest_path)

        return await self.process(reader.read(), reader.title, book_id=book_id)

    async def process(self, novel_text: str, title: str, book_id: str = None) -> dict:
        self.title = title
        book_id = book_id or self._ensure_book(title)
        logger.info(f"[{title}] Starting pipeline... (book_id={book_id})")

        # 1. Chunk the novel - use AdaptiveChunker directly since we have the text
        from src.utils.reader.text import AdaptiveChunker
        logger.info(f"[{title}] Chunking novel...")
        chunks = AdaptiveChunker().chunk(novel_text)
        logger.info(f"[{title}] Generated {len(chunks)} chunks")

        # 2. Generate MULTIPLE narrative nodes per chunk (multi-beat)
        all_nodes = []
        total_beats = 0
        for i, chunk in enumerate(chunks):
            logger.debug(f"[{title}] Processing chunk {i+1}/{len(chunks)}: {chunk.chapter or 'No chapter'}")

            # Generate chunk_id if not set
            chunk_id = chunk.id if chunk.id else f"chunk-{i:04d}"

            # Pass book_id to node_generator for tool queries
            self.node_generator.book_id = book_id

            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]

            total_beats += len(nodes)
            logger.info(f"[{title}] Chunk {i+1}: {len(nodes)} beats generated")

            # Link nodes and track state
            prev_node = all_nodes[-1] if all_nodes else None

            for j, node in enumerate(nodes):
                node.prev_node_id = prev_node.id if prev_node else ""

                # Ensure node has an ID
                if not node.id:
                    node.id = f"n-{i}-{j}"

                # Save to book repository (JSON files)
                self.book_storage.append_node(book_id, node)

                prev_node = node
                all_nodes.append(node)

        # Save chunks for tool queries
        self.book_storage.save_chunks(book_id, chunks)

        logger.info(f"[{title}] Total: {total_beats} narrative nodes generated")

        # 3. Build story structure
        logger.info(f"[{title}] Building story structure...")
        structure = self.structure_builder.build(all_nodes)
        logger.info(f"[{title}] Structure: opening={len(structure.opening)}, rising={len(structure.rising)}, climax={len(structure.climax)}, ending={len(structure.ending)}")

        # 4. Save structure
        if hasattr(self.db, 'save_structure'):
            self.db.save_structure(book_id, structure)
        logger.info(f"[{title}] Pipeline complete!")

        return {
            "title": title,
            "book_id": book_id,
            "nodes": all_nodes,
            "structure": structure
        }

    async def run_writing_agent(self, chunks: list[Chunk], nodes: list[NarrativeNode], title: str, book_id: str = None):
        """Run the podcast writing agent after nodes are generated."""
        from src.generation.podcast_writing_agent import PodcastWritingAgent
        if book_id is None:
            book_id = self._ensure_book(title)
        agent = PodcastWritingAgent(
            api_key=self.api_key,
            model=self.model,
        )
        return await agent.run(chunks, nodes, title, book_id)

    async def process_full(self, book_path: str, user_id: str = None):
        """Run the full pipeline: book → chunks → nodes → podcast manuscript."""
        from src.utils.reader import read_book
        import shutil

        if user_id:
            self.user_id = user_id

        reader = read_book(book_path)

        # Ensure book exists and save file
        book_id = self._ensure_book(reader.title)
        book_dir = Path(f"data/books/{book_id}")
        book_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(book_path).suffix.lower()
        dest_path = book_dir / f"book{suffix}"
        shutil.copy2(book_path, dest_path)

        # Chunk using book_id
        chunks = chunk_by_book_id(book_id)
        all_nodes = []
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.id if chunk.id else f"chunk-{i:04d}"
            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]
            for j, node in enumerate(nodes):
                if not node.id:
                    node.id = f"n-{i}-{j}"
                node.prev_node_id = all_nodes[-1].id if all_nodes else ""
                self.db.save_node(node, book_id)
                self.db.save_chunk(book_id, chunk_id, chunk.text, chunk.chapter, chunk.order or i)
                self.vector_store.add_node(node, chunk.text, book_id)
                all_nodes.append(node)

        structure = self.structure_builder.build(all_nodes)
        self.db.save_structure(book_id, structure)

        # New: write podcast manuscript
        manuscript = await self.run_writing_agent(chunks, all_nodes, reader.title, book_id)

        return manuscript
