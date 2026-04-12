"""Book analysis service with progress reporting."""
import asyncio
import os
from pathlib import Path
from typing import Optional, Callable
from src.core.chunker import ChapterChunker
from src.core.node_generator import NarrativeNodeGenerator
from src.core.structure_builder import StructureBuilder
from src.storage.database import Database
from src.storage.vector_store import VectorStore
from src.storage.json_storage import JsonStorage
from src.models.narrative_node import NarrativeNode
from src.models.story_structure import StoryStructure
from src.logging_config import debug


class Analyzer:
    """Analyzes books and generates narrative nodes with progress reporting."""

    def __init__(self, db_path: str = "data/story_summary.db", data_path: str = "data"):
        self.db = Database(db_path)
        self.json_storage = JsonStorage()
        self.chunker = ChapterChunker()
        self.node_generator = NarrativeNodeGenerator()
        self.structure_builder = StructureBuilder()
        self.vector_store = VectorStore(f"{data_path}/vectors")

    async def analyze(
        self,
        book_id: str,
        file_path: str,
        file_type: str,
        progress_callback: Optional[Callable] = None
    ):
        """Analyze a book file and generate narrative nodes.

        Args:
            book_id: The book ID
            file_path: Path to the book file
            file_type: 'epub' or 'txt'
            progress_callback: Async function(progress: int, message: str) for progress updates
        """
        async def report(progress: int, message: str):
            if progress_callback:
                await progress_callback(progress, message)

        await report(0, "开始解析文件...")

        # Read book content
        debug("analyzer", "book_id={} reading file type={}", book_id, file_type)
        if file_type == 'epub':
            text = await self._read_epub(file_path)
        else:
            text = await self._read_txt(file_path)
        debug("analyzer", "book_id={} text length={} chars", book_id, len(text))

        await report(5, "文件解析完成")

        # Chunk the novel
        await report(10, "开始分章...")
        debug("analyzer", "book_id={} starting chunking", book_id)
        chunks = self.chunker.chunk(text)
        debug("analyzer", "book_id={} chunked into {} chapters", book_id, len(chunks))
        await report(20, f"分章完成，共 {len(chunks)} 个章节")
        await asyncio.sleep(0.1)  # Small delay for UI update

        # Generate nodes
        all_nodes = []
        total_chunks = len(chunks)
        debug("analyzer", "book_id={} starting node generation for {} chunks", book_id, total_chunks)

        for i, chunk in enumerate(chunks):
            chunk_progress = 20 + int((i / total_chunks) * 60)
            await report(chunk_progress, f"正在分析第 {i+1}/{total_chunks} 章...")

            # Generate nodes for this chunk
            chunk_id = chunk.id if chunk.id else f"chunk-{i:04d}"
            self.node_generator.book_id = book_id
            debug("node_generator", "book_id={} chunk={}/{} generating nodes", book_id, i+1, total_chunks)

            try:
                nodes = await self.node_generator.generate_from_chunk(chunk)
                if not isinstance(nodes, list):
                    nodes = [nodes] if nodes else []
                debug("node_generator", "book_id={} chunk={} generated {} nodes", book_id, i, len(nodes))
            except Exception as e:
                debug("node_generator", "book_id={} chunk={} error={}", book_id, i, str(e))
                nodes = []

            # Link nodes
            prev_node = all_nodes[-1] if all_nodes else None
            for j, node in enumerate(nodes):
                node.prev_node_id = prev_node.id if prev_node else ""
                if not node.id:
                    node.id = f"n-{i}-{j}"
                all_nodes.append(node)
                prev_node = node

            # Save chunk and nodes
            self._save_chunk_and_nodes(book_id, chunk_id, chunk, nodes)

            await asyncio.sleep(0.05)  # Small delay for UI update

        debug("analyzer", "book_id={} node generation complete, total_nodes={}", book_id, len(all_nodes))
        await report(80, "节点生成完成，正在构建结构...")

        # Build structure
        debug("analyzer", "book_id={} building structure", book_id)
        structure = self.structure_builder.build(all_nodes)
        self._save_structure(book_id, structure)

        await report(95, "保存完成")

        # Update book status to completed
        debug("analyzer", "book_id={} updating status to completed", book_id)
        self.db.update_book_status(book_id, "completed")

        await report(100, "解析完成！")

        return {
            "nodes": all_nodes,
            "structure": structure,
            "total_chunks": total_chunks,
            "total_nodes": len(all_nodes)
        }

    async def _read_epub(self, file_path: str) -> str:
        """Read EPUB file and extract text."""
        import zipfile
        from bs4 import BeautifulSoup

        text_parts = []
        with zipfile.ZipFile(file_path, 'r') as z:
            # Find HTML files
            html_files = [f for f in z.namelist() if f.endswith('.html') or f.endswith('.xhtml') or f.endswith('.htm')]
            html_files.sort()

            for html_file in html_files:
                try:
                    content = z.read(html_file).decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(content, 'html.parser')
                    # Remove script and style tags
                    for tag in soup(['script', 'style']):
                        tag.decompose()
                    text = soup.get_text()
                    if text.strip():
                        text_parts.append(text)
                except Exception:
                    continue

        return "\n\n".join(text_parts)

    async def _read_txt(self, file_path: str) -> str:
        """Read TXT file with encoding detection."""
        encodings = ['utf-8', 'gbk', 'gb2312']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # Fallback: read as utf-8 with errors
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _save_chunk_and_nodes(self, book_id: str, chunk_id: str, chunk, nodes: list):
        """Save chunk and nodes to storage."""
        nodes_dir = f"data/books/{book_id}"
        os.makedirs(nodes_dir, exist_ok=True)

        # Save chunk
        chunk_file = f"{nodes_dir}/chunks.json"
        chunks_data = []
        if os.path.exists(chunk_file):
            chunks_data = self.json_storage.read(chunk_file) or []
        chunks_data.append({
            "id": chunk_id,
            "text": chunk.text,
            "chapter": getattr(chunk, 'chapter', None),
            "order": getattr(chunk, 'order', 0)
        })
        self.json_storage.write(chunk_file, chunks_data)

        # Save nodes
        nodes_file = f"{nodes_dir}/nodes.json"
        nodes_data = []
        if os.path.exists(nodes_file):
            nodes_data = self.json_storage.read(nodes_file) or []
        for node in nodes:
            if node:
                nodes_data.append(node.to_dict() if hasattr(node, 'to_dict') else node)
        self.json_storage.write(nodes_file, nodes_data)

    def _save_structure(self, book_id: str, structure: StoryStructure):
        """Save story structure to storage."""
        nodes_dir = f"data/books/{book_id}"
        os.makedirs(nodes_dir, exist_ok=True)
        structure_file = f"{nodes_dir}/structure.json"
        self.json_storage.write(structure_file, structure.model_dump())
