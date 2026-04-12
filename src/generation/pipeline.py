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
from src.generation.polish import PolishAgent
from src.logging_config import debug


class ManuscriptPipeline:
    """口播稿生成 Pipeline"""

    def __init__(self, output_dir: str = "output", debug_mode: bool = False):
        self.output_dir = output_dir
        self.debug_mode = debug_mode
        self.db = Database()
        self.json_storage = JsonStorage()
        self.writer = ChapterWriter(debug_mode=debug_mode)
        self.polisher = PolishAgent(debug_mode=debug_mode)

    async def run(self, book_id: str) -> ManuscriptResult:
        """运行生成流程"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        debug("pipeline", "[1] 书籍信息: book_id={} title={}", book_id, book.title)

        # 2. 加载或创建状态
        state_path = WritingState.get_state_path(book_id, self.output_dir, book.title)
        if state_path.exists():
            state = WritingState.load(state_path)
            debug("pipeline", "[2] 恢复状态: phase={} chunk_index={} drafts_count={}",
                  state.phase.value, state.current_chunk_index, len(state.drafts))
        else:
            state = WritingState(book_id=book_id, book_title=book.title)
            debug("pipeline", "[2] 新建状态")

        # 3. 加载 nodes 和 chunks
        nodes = self._load_nodes(book_id)
        chunks = self._load_chunks(book_id)
        debug("pipeline", "[3] 加载数据: nodes_count={} chunks_count={}", len(nodes), len(chunks))

        # 4. [PREPARE] 阶段
        if state.phase == WritingPhase.PREPARE:
            debug("pipeline", "[4] PREPARE 阶段")
            await self._phase_prepare(nodes)
            state.phase = WritingPhase.WRITING
            state.save(state_path)

        # 5. [WRITING] 阶段
        debug("pipeline", "[5] WRITING 阶段: 从 chunk {} 开始", state.current_chunk_index)
        context = WritingContext()
        if state.drafts:
            context.drafts = state.drafts
            context._update_summary()
            debug("pipeline", "[5] 恢复已有草稿: drafts_count={}", len(state.drafts))

        while state.current_chunk_index < len(chunks):
            chunk = chunks[state.current_chunk_index]
            chunk_nodes = [n for n in nodes if n.parent_chunk_id == chunk.id]

            debug("pipeline", "[5.1] 处理 Chunk {}/{}: chunk_id={} title={}",
                  state.current_chunk_index + 1, len(chunks), chunk.id, chunk.chapter or '无标题')
            debug("pipeline", "[5.2] 本章节点数: {} 个", len(chunk_nodes))

            # 打印节点信息
            for i, n in enumerate(chunk_nodes):
                debug("pipeline", "[5.3] 节点{}: role={} scene={}",
                      i+1, n.narrative_role, n.scene[:50] if n.scene else '无')

            prompt_context = context.build_prompt_context(chunk, chunk_nodes)
            debug("pipeline", "[5.4] 上下文摘要长度: {} 字", len(prompt_context))

            chapter_text = await self.writer.write(
                chunk=chunk,
                nodes=chunk_nodes,
                context_summary=prompt_context,
            )

            debug("pipeline", "[5.5] 生成章节长度: {} 字", len(chapter_text))
            if self.debug_mode and chapter_text:
                preview = chapter_text[:200].replace('\n', ' ')
                debug("pipeline", "[5.6] 章节预览: {}...", preview)

            context.add_draft(chunk.id, chapter_text)
            state.drafts = context.drafts
            state.current_chunk_index += 1
            state.save(state_path)
            debug("pipeline", "[5.7] 已保存状态: chunk_index={}", state.current_chunk_index)

        # 6. [POLISHING] 阶段
        debug("pipeline", "[6] POLISHING 阶段: 开始润色")
        state.phase = WritingPhase.POLISHING
        state.save(state_path)

        chunks_dict = {c.id: c for c in chunks}
        debug("pipeline", "[6.1] 润色参数: drafts_count={} chunks_count={}",
              len(context.drafts), len(chunks_dict))

        polished = await self.polisher.polish(context.drafts, chunks_dict)

        debug("pipeline", "[6.2] 润色完成: {} 字", len(polished))
        if self.debug_mode and polished:
            preview = polished[:200].replace('\n', ' ')
            debug("pipeline", "[6.3] 润色预览: {}...", preview)

        # 7. 保存最终稿
        safe = re.sub(r'[<>:"/\\|?*]', '_', book.title)
        out_dir = Path(self.output_dir) / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript.txt").write_text(polished, encoding="utf-8")

        debug("pipeline", "[7] 已保存到: {}", out_dir / "manuscript.txt")

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
        book = self.db.get_book(book_id)
        nodes_file = f"{book.nodes_file_path}/nodes.json"
        data = self.json_storage.read(nodes_file)

        if isinstance(data, dict):
            nodes_list = data.get("nodes", [])
        else:
            nodes_list = data or []

        return [NarrativeNode.model_validate(n) for n in nodes_list]

    def _load_chunks(self, book_id: str) -> list[Chunk]:
        book = self.db.get_book(book_id)
        chunks_file = f"{book.nodes_file_path}/chunks.json"
        data = self.json_storage.read(chunks_file) or []

        return [Chunk.model_validate(c) for c in data]

    async def _phase_prepare(self, nodes: list[NarrativeNode]) -> None:
        """[PREPARE] 阶段：加载所有 nodes 建立全局理解"""
        debug("pipeline", "[PREPARE] 收到 {} 个节点", len(nodes))
        # 后续扩展：LLM 分析节点生成全局摘要
