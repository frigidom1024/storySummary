import logging
import uuid
from pathlib import Path
from src.core.chunker import chunk_by_book_id
from src.core.node_generator import NarrativeNodeGenerator
from src.core.structure_builder import StructureBuilder
from src.storage.database import Database
from src.storage.vector_store import VectorStore
from src.storage.book_repository import book_repository
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
        logger: logging.Logger = logger
    ):
        self.api_key = api_key
        self.model = model
        self.user_id = user_id or "default-user"
        self.node_generator = NarrativeNodeGenerator(api_key=api_key, model=model)
        self.structure_builder = StructureBuilder()
        self.db = Database(db_path)
        self.vector_store = VectorStore(vector_store_path)
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

        # Store original text chunks
        if chunks:
            for i, chunk in enumerate(chunks):
                chunk_id = chunk.id
                if hasattr(chunk, 'text') and chunk.text:
                    chapter_id = chunk.chapter or f"chapter_{i}"
                    self.vector_store.add_original_text(
                        book_id=book_id,
                        text=chunk.text,
                        chapter_id=chapter_id,
                        chunk_id=chunk_id
                    )
                    book_repository.append_chunk(book_id, chunk)
                else:
                    logger.warning(f"[{title}] Chunk {chunk_id} has no text, skipping.")
            logger.info(f"[{title}] Stored {len(chunks)} original text chunks")

        

        # 2. Generate MULTIPLE narrative nodes per chunk (multi-beat)
        all_nodes = []
        total_beats = 0

        # For testing, limit to first N chunks to avoid long processing time
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"[{title}] Processing chunk {i+1}/{len(chunks)}: {chunk.chapter or 'No chapter'}")

            # Generate chunk_id if not set
            chunk_id = chunk.id if chunk.id else f"chunk-{i:04d}"

            # Pass book_id to node_generator for tool queries
            self.node_generator.book_id = book_id
            self.node_generator.agent2.book_id = book_id
            self.node_generator.agent3.book_id = book_id
            self.node_generator.agent4.book_id = book_id

            nodes = await self.node_generator.generate_from_chunk(chunk)
            if not isinstance(nodes, list):
                nodes = [nodes]

            total_beats += len(nodes)
            logger.info(f"[{title}] Chunk {i+1}: {len(nodes)} beats generated")

            # Add nodes to all_nodes
            all_nodes.extend(nodes)
            
            # Store narrative nodes for this chunk
            if nodes:
                self.vector_store.add_nodes(book_id, nodes)
                logger.info(f"[{title}] Stored {len(nodes)} narrative nodes from chunk {i+1}")

            # Save to BookRepository for persistence (append each node)
            if nodes:
                for node in nodes:
                    book_repository.append_node(book_id, node)


        # Build structure
        if all_nodes:
            # 全局链接 nodes 的 prev/next 关系
            all_nodes = NarrativeNodeGenerator.link_nodes_globally(all_nodes, chunks)
            structure = self.structure_builder.build(all_nodes)
        
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
