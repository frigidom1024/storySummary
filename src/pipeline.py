import logging
from typing import List
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
        logger: logging.Logger = logger
    ):
        self.api_key = api_key
        self.model = model
        self.node_generator = NarrativeNodeGenerator(api_key=api_key, model=model)
        self.structure_builder = StructureBuilder()
        self.db = Database(db_path)
        self.vector_store = VectorStore(vector_store_path)

    async def process(self, chunks: List[Chunk], title: str, book_id: str) -> dict:
        logger.info(f"[{title}] Starting pipeline... (book_id={book_id})")

        # chunks 已经是 reader 分好的章节，无需重新分块
        logger.info(f"[{title}] Using {len(chunks)} pre-chunked chapters")

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

        # Agent3: 丰富 chunk 的 discussion_prompts
        # 在节点生成完成后调用，独立于 node 生成流程
        from src.core.agents.agent3_interesting_finder import Agent3InterestingFinder
        agent3 = Agent3InterestingFinder(api_key=self.api_key, book_id=book_id)
        logger.info(f"[{title}] Agent3: Processing discussion prompts for {len(chunks)} chunks...")
        for i, chunk in enumerate(chunks):
            logger.debug(f"[{title}] Agent3: Processing chunk {i+1}/{len(chunks)}: {chunk.chapter or 'untitled'}")
            updated_chunk = await agent3.process_chunk(chunk)
            chunks[i] = updated_chunk
        logger.info(f"[{title}] Agent3: discussion prompts enriched")

        # 保存更新后的 chunks
        book_repository.update_chunks(book_id, chunks)
        logger.info(f"[{title}] Updated {len(chunks)} chunks with discussion_prompts")

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
    
    # 函数弃用
    async def run_writing_agent(self, chunks: list[Chunk], nodes: list[NarrativeNode], title: str, book_id: str):
        """Run the podcast writing agent after nodes are generated."""
        from src.generation.podcast_writing_agent import PodcastWritingAgent
        agent = PodcastWritingAgent(
            api_key=self.api_key,
            model=self.model,
        )
        return await agent.run(chunks, nodes, title, book_id)

    # 函数弃用
    async def process_full(self, book_id: str, title: str, chunks: List[Chunk]):
        """Run the full pipeline: chunks → nodes → podcast manuscript."""
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

        manuscript = await self.run_writing_agent(chunks, all_nodes, title, book_id)

        return manuscript
