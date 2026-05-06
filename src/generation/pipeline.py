import inspect
import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

from src.generation.models import ManuscriptResult
from src.generation.agents.outline import OutlineAgent
from src.generation.agents.polish import PolishAgent
from src.generation.state import PipelinePhase, WritingState
from src.generation.agents.models import Draft
from src.generation.agents.style import StyleLearningAgent, StyleProfile
from src.generation.agents.writer import ChapterWriter
from src.generation.agents.guide import GuideAgent
from src.logging_config import debug
from src.storage.book_repository import book_repository
from src.storage.database import Database
from src.storage.manuscript_repository import manuscript_repository


class ManuscriptPipeline:
    """精简版口播稿生成流程。"""

    def __init__(
        self,
        output_dir: str = "output",
        debug_mode: bool = False,
        style_key: str = None,
        custom_rules: str = None,
        reference_script: str = None,
        progress_callback: Optional[Callable[[int, str], Any]] = None,
    ):
        self.output_dir = output_dir
        self.debug_mode = debug_mode
        self.style_key = style_key
        self.custom_rules = custom_rules
        self.reference_script = reference_script
        self.progress_callback = progress_callback

        self.db = Database()
        self.outliner = OutlineAgent(debug_mode=debug_mode)
        self.style_learner = StyleLearningAgent(debug_mode=debug_mode)
        self.writer = ChapterWriter(debug_mode=debug_mode)
        self.guide = GuideAgent(debug_mode=debug_mode)
        self.polisher = PolishAgent(debug_mode=debug_mode)

        self.style_profile: Optional[StyleProfile] = None

    def _is_phase_done(self, book_id: str, phase: PipelinePhase) -> bool:
        """检查指定阶段是否已完成"""
        status = manuscript_repository.manuscript_status(book_id)
        if phase == PipelinePhase.OUTLINING:
            return status.get("synopsis") and status.get("outline")
        elif phase == PipelinePhase.STYLE_LEARNING:
            return status.get("style_profile")
        elif phase == PipelinePhase.WRITING:
            return status.get("drafts", {}).get("total", 0) > 0
        elif phase == PipelinePhase.POLISHING:
            return status.get("final_manuscript")
        elif phase == PipelinePhase.DONE:
            return False
        return False

    async def run(self, book_id: str) -> ManuscriptResult:
        book = self.db.get_book(book_id)
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        chunks = book_repository.load_chunks(book_id)
        nodes = book_repository.load_nodes(book_id)
        if not chunks:
            raise ValueError("No chunks found for this book")

        state_path = WritingState.get_state_path(book_id, self.output_dir, book.title)
        state = WritingState.load(state_path) if state_path.exists() else WritingState(
            book_id=book_id,
            book_title=book.title,
        )

        # ========== 阶段1：生成梗概和结构 ==========
        if state.phase == PipelinePhase.OUTLINING or not self._is_phase_done(book_id, PipelinePhase.OUTLINING):
            await self._run_outline_phase(book_id, book.title, chunks, nodes, state, state_path)
            state.phase = PipelinePhase.STYLE_LEARNING
            state.save(state_path)

        # ========== 阶段2：学习风格参考 ==========
        if state.phase == PipelinePhase.STYLE_LEARNING or not self._is_phase_done(book_id, PipelinePhase.STYLE_LEARNING):
            self.style_profile = await self._run_style_phase(book_id, book.title, state, state_path)
            
            state.phase = PipelinePhase.WRITING
            state.save(state_path)

        # ========== 阶段3：迭代写草稿 ==========
        if state.phase == PipelinePhase.WRITING or not self._is_phase_done(book_id, PipelinePhase.WRITING):
            await self._run_writing_phase(book_id, chunks, nodes, state, state_path)
            state.phase = PipelinePhase.POLISHING
            state.save(state_path)

        # ========== 阶段4：润色 ==========
        if state.phase == PipelinePhase.POLISHING or not self._is_phase_done(book_id, PipelinePhase.POLISHING):
            try:
                await self._run_polish_phase(book_id, state, state_path)
            except Exception as e:
                raise RuntimeError(f"Polish phase failed: {e}") from e
            state.phase = PipelinePhase.DONE
            state.save(state_path)

        await self._report_progress(100, "生成完成")

        all_drafts = manuscript_repository.load_all_drafts(book_id)
        drafts = [
            Draft(section_id=k, draft_type=v.get("type", ""), content=v.get("content", ""))
            for k, v in all_drafts.items()
        ]

        return ManuscriptResult(
            title=book.title,
            book_id=book_id,
            drafts=drafts,
            phase=state.phase.value,
        )

    async def _report_progress(self, progress: int, message: str) -> None:
        if not self.progress_callback:
            return
        result = self.progress_callback(progress, message)
        if inspect.isawaitable(result):
            await result

    async def _run_outline_phase(self, book_id: str, book_title: str, chunks, nodes, state, state_path):
        """阶段1：生成梗概和结构"""
        await self._report_progress(5, "正在生成故事梗概和口播稿结构...")

        story_synopsis, manuscript_outline_json = await self.outliner.build_outline(
            book_id=book_id,
            chunks=chunks,
            nodes=nodes,
            reference_script=self.reference_script,
        )

        # 存储梗概
        manuscript_repository.save_synopsis(book_id, story_synopsis)

        # 存储结构
        try:
            outline_data = json.loads(manuscript_outline_json)
            manuscript_repository.save_outline(book_id, outline_data)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Failed to parse or save outline: {e}") from e

        await self._report_progress(20, "梗概和结构生成完成")

    async def _run_style_phase(self, book_id: str, book_title: str, state, state_path):
        """阶段2：学习风格参考"""
        await self._report_progress(25, "正在学习风格参考...")

        if self.reference_script:
            style_profile = await self.style_learner.learn_profile(self.reference_script)
            manuscript_repository.save_style_profile(book_id, style_profile.model_dump())
            return style_profile
        return None

    async def _run_writing_phase(self, book_id: str, chunks, nodes, state, state_path):
        """阶段3：迭代写草稿 - 遍历 outline 结构，根据类型调用不同 AI"""
        outline_data = manuscript_repository.load_outline(book_id)
        outline_list = outline_data if isinstance(outline_data, list) else []
        style_profile = None
        if manuscript_repository.has_style_profile(book_id):
            profile_dict = manuscript_repository.load_style_profile(book_id)
            style_profile = StyleProfile(**profile_dict)

        # 构建 chunks 映射
        chunks_by_type = {}
        for chunk in chunks:
            chunks_by_type.setdefault(chunk.content_type, []).append(chunk)
        nodes_by_chunk = {}
        for chunk in chunks:
            nodes_by_chunk[chunk.id] = [n for n in nodes if n.parent_chunk_id == chunk.id]

        total_sections = len(outline_list)
        for i, section in enumerate(outline_list):
            section_id = section.get("section", f"section-{i}")
            section_type = section.get("type")
            chapter_num = section.get("chapter")

            if manuscript_repository.load_draft(book_id, section_id):
                continue

            await self._report_progress(25 + int((i / total_sections) * 55), f"正在生成 {section_id}...")

            if section_type == "author_intro":
                intro_chunks = chunks_by_type.get("author_intro", [])
                if intro_chunks:
                    chunk = intro_chunks[0]
                    text = await self.guide.write_intro(
                        book_id=book_id,
                        chunk=chunk,
                        style_key=self.style_key,
                        intro_style=style_profile.intro_style if style_profile else None,
                    )
                    if text:
                        manuscript_repository.save_draft(book_id, section_id, "intro", text)

            elif section_type == "story_content":
                chunk_id = section.get("chunk_id")
                chunk = next((c for c in chunks if c.id == chunk_id), None)
                if chunk:
                    chunk_nodes = nodes_by_chunk.get(chunk.id, [])
                    completed_drafts = []
                    for d in manuscript_repository.load_all_drafts(book_id).values():
                        try:
                            completed_drafts.append(Draft(**d))
                        except Exception as e:
                            debug("pipeline", "[_run_writing_phase] Failed to load draft: {}", e)
                    text = await self.writer.write(
                        chunk=chunk,
                        nodes=chunk_nodes,
                        completed_drafts=completed_drafts,
                        book_id=book_id,
                        style_key=self.style_key,
                        custom_rules=self.custom_rules,
                        reference_script=self.reference_script,
                        outline=outline_list,
                        narrative_style=style_profile.narrative_style if style_profile else None,
                    )
                    if text:
                        manuscript_repository.save_draft(book_id, section_id, "chapter", text)

            elif section_type == "reflection":
                reflection_chunks = chunks_by_type.get("appendix", []) + chunks_by_type.get("reflection", [])
                if reflection_chunks:
                    chunk = reflection_chunks[0]
                    completed_contents = [d["content"] for d in manuscript_repository.load_all_drafts(book_id).values()]
                    text = await self.guide.write_reflection(
                        book_id=book_id,
                        chunk=chunk,
                        completed_drafts=completed_contents,
                        style_key=self.style_key,
                        reflection_style=style_profile.reflection_style if style_profile else None,
                    )
                    if text:
                        manuscript_repository.save_draft(book_id, section_id, "reflection", text)

        await self._report_progress(80, "草稿生成完成")

    async def _run_polish_phase(self, book_id: str, state, state_path):
        """阶段4：整合草稿为完整口播稿"""
        await self._report_progress(85, "正在整合口播稿...")

        try:
            all_drafts = manuscript_repository.load_all_drafts(book_id)
            drafts_list = list(all_drafts.values())

            synopsis = manuscript_repository.load_synopsis(book_id) or ""
            book_info = {
                "title": state.book_title,
                "synopsis": synopsis,
            }

            final_manuscript = await self.polisher.polish(drafts_list, book_info)
            manuscript_repository.save_final_manuscript(book_id, final_manuscript)
        except Exception as e:
            raise RuntimeError(f"Failed to polish or save manuscript: {e}") from e

        await self._report_progress(95, "整合完成")
