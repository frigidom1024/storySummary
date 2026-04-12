import os
import re
import json
from pathlib import Path
from typing import Optional, Any, Callable
from datetime import datetime

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


class DebugRecord:
    """记录每一步的完整内容"""

    def __init__(self):
        self.data: dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "phases": {}
        }

    def add_phase(self, name: str, content: dict):
        self.data["phases"][name] = content

    def add_prepare(self, nodes: list):
        self.data["phases"]["prepare"] = {
            "nodes_count": len(nodes),
            "nodes": [self._node_to_dict(n) for n in nodes]
        }

    def add_writing_chapter(self, index: int, chunk: Chunk, nodes: list,
                           prompt_context: str, generated_text: str):
        self.data["phases"][f"writing_chapter_{index}"] = {
            "chunk_id": chunk.id,
            "chunk_title": chunk.chapter,
            "chunk_text_length": len(chunk.text),
            "chunk_text_preview": chunk.text[:500],
            "nodes": [self._node_to_dict(n) for n in nodes],
            "prompt_context": prompt_context,
            "generated_text": generated_text,
            "generated_text_length": len(generated_text)
        }

    def add_polish(self, input_text: str, output_text: str):
        self.data["phases"]["polish"] = {
            "input_length": len(input_text),
            "input_text": input_text,
            "output_length": len(output_text),
            "output_text": output_text
        }

    def add_result(self, manuscript_text: str, chapters_written: int, total_chunks: int):
        self.data["result"] = {
            "manuscript_length": len(manuscript_text),
            "manuscript_text": manuscript_text,
            "chapters_written": chapters_written,
            "total_chunks": total_chunks
        }

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _node_to_dict(self, n: NarrativeNode) -> dict:
        return {
            "id": n.id,
            "scene": n.scene,
            "situation": n.situation,
            "narrative_role": n.narrative_role,
            "turning_point": n.turning_point,
            "emotional_arc": n.emotional_arc,
            "mood_tone": n.mood_tone,
            "characters": [{"name": c.name} for c in (n.characters or [])]
        }


class ManuscriptPipeline:
    """口播稿生成 Pipeline"""

    def __init__(self, output_dir: str = "output", debug_mode: bool = False,
                 style_key: str = None, custom_rules: str = None, reference_script: str = None,
                 progress_callback: Callable[[int, str], None] = None):
        self.output_dir = output_dir
        self.debug_mode = debug_mode
        self.style_key = style_key
        self.custom_rules = custom_rules
        self.reference_script = reference_script
        self.progress_callback = progress_callback
        self.db = Database()
        self.json_storage = JsonStorage()
        self.writer = ChapterWriter(debug_mode=debug_mode)
        self.polisher = PolishAgent(debug_mode=debug_mode)
        self.debug_record: Optional[DebugRecord] = None

    def _report_progress(self, progress: int, message: str):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(progress, message)

    async def run(self, book_id: str) -> ManuscriptResult:
        """运行生成流程"""
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        debug("pipeline", "[1] 书籍信息: book_id={} title={}", book_id, book.title)

        # 初始化调试记录
        if self.debug_mode:
            self.debug_record = DebugRecord()

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

        if self.debug_mode:
            self.debug_record.data["book_info"] = {
                "book_id": book_id,
                "title": book.title,
                "nodes_count": len(nodes),
                "chunks_count": len(chunks)
            }
            self.debug_record.data["all_chunks"] = [
                {
                    "id": c.id,
                    "chapter": c.chapter,
                    "text_length": len(c.text),
                    "text_preview": c.text[:1000]
                }
                for c in chunks
            ]

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

            # 报告进度：开始写章节
            chapter_title = chunk.chapter or f"第{chunk.order + 1}章"
            progress = int((state.current_chunk_index / len(chunks)) * 80)  # 写作阶段占80%
            self._report_progress(progress, f"正在生成 {chapter_title}...")

            debug("pipeline", "[5.1] 处理 Chunk {}/{}: chunk_id={} title={}",
                  state.current_chunk_index + 1, len(chunks), chunk.id, chunk.chapter or '无标题')
            debug("pipeline", "[5.2] 本章节点数: {} 个", len(chunk_nodes))

            prompt_context = context.build_prompt_context(chunk, chunk_nodes)

            chapter_text = await self.writer.write(
                chunk=chunk,
                nodes=chunk_nodes,
                context_summary=prompt_context,
                style_key=self.style_key,
                custom_rules=self.custom_rules,
                reference_script=self.reference_script,
            )

            # 报告进度：章节完成
            self._report_progress(progress + 5, f"已完成 {chapter_title}")
            debug("pipeline", "[5.5] 生成章节长度: {} 字", len(chapter_text))

            # 记录调试信息
            if self.debug_mode:
                self.debug_record.add_writing_chapter(
                    index=state.current_chunk_index + 1,
                    chunk=chunk,
                    nodes=chunk_nodes,
                    prompt_context=prompt_context,
                    generated_text=chapter_text
                )

            context.add_draft(chunk.id, chapter_text)
            state.drafts = context.drafts
            state.current_chunk_index += 1
            state.save(state_path)
            debug("pipeline", "[5.7] 已保存状态: chunk_index={}", state.current_chunk_index)

        # 6. [POLISHING] 阶段
        debug("pipeline", "[6] POLISHING 阶段: 开始润色")
        state.phase = WritingPhase.POLISHING
        state.save(state_path)
        self._report_progress(85, "正在润色全文...")

        chunks_dict = {c.id: c for c in chunks}

        full_draft = context.full_draft()

        if self.debug_mode:
            self.debug_record.data["polish_input"] = {
                "drafts_count": len(context.drafts),
                "full_draft_length": len(full_draft),
                "full_draft": full_draft,
                "chunks_for_reference": {
                    cid: {
                        "chapter": c.chapter,
                        "text_length": len(c.text),
                        "text": c.text
                    }
                    for cid, c in chunks_dict.items()
                }
            }

        polished = await self.polisher.polish(context.drafts, chunks_dict)

        debug("pipeline", "[6.2] 润色完成: {} 字", len(polished))

        if self.debug_mode:
            self.debug_record.add_polish(full_draft, polished)

        # 7. 保存最终稿
        safe = re.sub(r'[<>:"/\\|?*]', '_', book.title)
        out_dir = Path(self.output_dir) / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript.txt").write_text(polished, encoding="utf-8")

        debug("pipeline", "[7] 已保存到: {}", out_dir / "manuscript.txt")

        state.phase = WritingPhase.DONE
        state.save(state_path)

        # 保存调试记录
        if self.debug_mode:
            self.debug_record.add_result(polished, len(chunks), len(chunks))
            debug_path = out_dir / "debug_record.json"
            self.debug_record.save(debug_path)
            debug("pipeline", "[DEBUG] 调试记录已保存到: {}", debug_path)

        # 报告进度：完成
        self._report_progress(100, "生成完成")

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
        if self.debug_mode and self.debug_record:
            self.debug_record.add_prepare(nodes)
