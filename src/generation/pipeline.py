import os
import re
from pathlib import Path
from typing import Optional

from src.models.narrative_node import NarrativeNode
from src.models.chunk import Chunk
from src.generation.models import ManuscriptResult, ChapterDraft
from src.storage.database import Database
from src.storage.json_storage import JsonStorage
from src.generation.state import WritingState, WritingPhase
from src.generation.context import WritingContext
from src.generation.writer import ChapterWriter
from src.generation.polish import PolishPass


class ManuscriptPipeline:
    """口播稿生成 Pipeline"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.db = Database()
        self.json_storage = JsonStorage()
        self.writer = ChapterWriter()
        self.polisher = PolishPass()

    async def run(self, book_id: str) -> ManuscriptResult:
        """运行生成流程"""
        # 1. 获取书籍信息
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        # 2. 加载或创建状态
        state_path = WritingState.get_state_path(book_id, self.output_dir, book.title)
        if state_path.exists():
            state = WritingState.load(state_path)
        else:
            state = WritingState(book_id=book_id, book_title=book.title)

        # 3. 加载所有 nodes
        nodes = self._load_nodes(book_id)
        chunks = self._load_chunks(book_id)

        # 4. [PREPARE] 阶段：喂 nodes 给 AI
        if state.phase == WritingPhase.PREPARE:
            await self._phase_prepare(nodes)
            state.phase = WritingPhase.WRITING
            state.save(state_path)

        # 5. [WRITING] 阶段：逐 chunk 生成
        context = WritingContext()
        if state.drafts:
            context.drafts = state.drafts
            context._update_summary()

        while state.current_chunk_index < len(chunks):
            chunk = chunks[state.current_chunk_index]
            chunk_nodes = [n for n in nodes if n.parent_chunk_id == chunk.id]

            prompt_context = context.build_prompt_context(chunk, chunk_nodes)
            chapter_text = await self.writer.write(
                chunk=chunk,
                nodes=chunk_nodes,
                context_summary=prompt_context,
            )

            context.add_draft(chunk.id, chapter_text)
            state.drafts = context.drafts
            state.current_chunk_index += 1
            state.save(state_path)

        # 6. [POLISHING] 阶段
        state.phase = WritingPhase.POLISHING
        state.save(state_path)

        polished = await self.polisher.polish(context.full_draft())

        # 7. 保存最终稿
        safe = re.sub(r'[<>:"/\\|?*]', '_', book.title)
        out_dir = Path(self.output_dir) / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript.txt").write_text(polished, encoding="utf-8")

        state.phase = WritingPhase.DONE
        state.save(state_path)

        return ManuscriptResult(
            title=book.title,
            drafts=[ChapterDraft(chunk_id="final", chapter_text=polished)],
            phase=state.phase.value,
            chapters_written=len(chunks),
            total_chunks=len(chunks),
        )

    def _load_nodes(self, book_id: str) -> list[NarrativeNode]:
        """加载所有节点"""
        book = self.db.get_book(book_id)
        nodes_file = f"{book.nodes_file_path}/nodes.json"
        data = self.json_storage.read(nodes_file)

        if isinstance(data, dict):
            nodes_list = data.get("nodes", [])
        else:
            nodes_list = data or []

        return [NarrativeNode.model_validate(n) for n in nodes_list]

    def _load_chunks(self, book_id: str) -> list[Chunk]:
        """加载所有 chunk"""
        book = self.db.get_book(book_id)
        chunks_file = f"{book.nodes_file_path}/chunks.json"
        data = self.json_storage.read(chunks_file) or []

        return [Chunk.model_validate(c) for c in data]

    async def _phase_prepare(self, nodes: list[NarrativeNode]) -> None:
        """[PREPARE] 阶段：加载所有 nodes 建立全局理解"""
        # 当前为简化版本，直接跳过
        # 后续可扩展：调用 LLM 分析所有 nodes，生成全局摘要
        pass
