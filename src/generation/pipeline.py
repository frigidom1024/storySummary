import inspect
import re
from pathlib import Path
from typing import Any, Callable, Optional

from src.generation.models import ManuscriptResult
from src.generation.agents.outline import OutlineAgent
from src.generation.polish import PolishAgent
from src.generation.state import WritingPhase, WritingState
from src.generation.agents.style import StyleLearningAgent
from src.generation.writer import ChapterWriter
from src.logging_config import debug
from src.storage.book_repository import book_repository
from src.storage.database import Database


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
        self.polisher = PolishAgent(debug_mode=debug_mode)

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

        await self._report_progress(5, "正在构建全书故事大纲...")
        outline = await self._load_or_build_outline(book_id, book.title, chunks, nodes)
        style_profile = await self._load_or_build_style_profile(book.title, self.reference_script)
        total = len(chunks)
        debug("pipeline", "[RUN] title={} chunks={}", book.title, total)

        while state.current_chunk_index < total:
            idx = state.current_chunk_index
            chunk = chunks[idx]
            chunk_nodes = [n for n in nodes if n.parent_chunk_id == chunk.id]
            chapter_name = chunk.chapter or f"第{chunk.order + 1}章"

            await self._report_progress(int((idx / total) * 80), f"正在生成 {chapter_name}...")
            chapter_text = await self.writer.write(
                chunk=chunk,
                nodes=chunk_nodes,
                completed_drafts=state.drafts,
                global_outline=outline,
                book_id=book_id,
                all_chunks=chunks,
                all_nodes=nodes,
                style_profile=style_profile,
                style_key=self.style_key,
                custom_rules=self.custom_rules,
                reference_script=self.reference_script,
            )
            state.add_draft(chunk.id, chapter_text)
            state.save(state_path)
            await self._report_progress(int((state.current_chunk_index / total) * 80), f"已完成 {chapter_name}")

        state.phase = WritingPhase.POLISHING
        state.save(state_path)
        await self._report_progress(85, "正在润色全文...")

        full_draft = state.full_draft()
        polished = await self.polisher.polish(full_draft, chunks)
        self._save_output(book.title, polished)

        state.phase = WritingPhase.DONE
        state.save(state_path)
        await self._report_progress(100, "生成完成")

        return ManuscriptResult(
            title=book.title,
            drafts=state.drafts,
            phase=state.phase.value,
            chapters_written=len(state.drafts),
            total_chunks=total,
        )

    async def _report_progress(self, progress: int, message: str) -> None:
        if not self.progress_callback:
            return
        result = self.progress_callback(progress, message)
        if inspect.isawaitable(result):
            await result

    def _save_output(self, title: str, manuscript: str) -> None:
        safe = re.sub(r'[<>:"/\\|?*]', "_", title)
        out_dir = Path(self.output_dir) / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript.txt").write_text(manuscript, encoding="utf-8")

    async def _load_or_build_outline(self, book_id: str, title: str, chunks: list, nodes: list) -> str:
        outline_path = self._outline_path(title)
        if outline_path.exists():
            return outline_path.read_text(encoding="utf-8")

        try:
            outline = await self.outliner.build_outline(book_id, chunks, nodes)
        except Exception as exc:
            debug("pipeline", "[OUTLINE] fallback due to error: {}", str(exc))
            outline = self._build_outline_fallback(chunks, nodes)

        outline_path.parent.mkdir(parents=True, exist_ok=True)
        outline_path.write_text(outline, encoding="utf-8")
        return outline

    def _outline_path(self, title: str) -> Path:
        safe = re.sub(r'[<>:"/\\|?*]', "_", title)
        return Path(self.output_dir) / safe / "outline.txt"

    async def _load_or_build_style_profile(self, title: str, reference_script: Optional[str]) -> str:
        if not reference_script:
            return ""

        profile_path = self._style_profile_path(title)
        if profile_path.exists():
            return profile_path.read_text(encoding="utf-8")

        try:
            profile = await self.style_learner.learn(reference_script)
        except Exception as exc:
            debug("pipeline", "[STYLE] fallback due to error: {}", str(exc))
            profile = self._build_style_profile_fallback(reference_script)

        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(profile, encoding="utf-8")
        return profile

    def _style_profile_path(self, title: str) -> Path:
        safe = re.sub(r'[<>:"/\\|?*]', "_", title)
        return Path(self.output_dir) / safe / "style_profile.txt"

    def _build_style_profile_fallback(self, reference_script: str) -> str:
        text = reference_script.strip().replace("\r\n", "\n")
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        short_lines = [ln for ln in lines if len(ln) <= 30]
        colloquial_hits = [k for k in ["是吧", "怎么说呢", "你像", "说实话"] if k in text]
        return (
            "风格总览:\n"
            f"- 参考稿总长度: {len(text)} 字\n"
            f"- 行数: {len(lines)}\n"
            f"- 短句占比(<=30字): {int((len(short_lines)/max(1,len(lines)))*100)}%\n"
            f"- 常见口头表达: {', '.join(colloquial_hits) if colloquial_hits else '未显著识别'}\n"
            "- 写作建议: 保持口语化、短句推进、避免书面化总结。"
        )

    def _build_outline_fallback(self, chunks: list, nodes: list) -> str:
        nodes_by_chunk: dict[str, list] = {}
        for node in nodes:
            nodes_by_chunk.setdefault(node.parent_chunk_id, []).append(node)

        lines = []
        for idx, chunk in enumerate(chunks, start=1):
            chapter_name = chunk.chapter or f"第{idx}章"
            chapter_nodes = nodes_by_chunk.get(chunk.id, [])
            if chapter_nodes:
                beats = [n.scene for n in chapter_nodes[:3] if n.scene]
                preview = " / ".join(beats) if beats else chunk.text[:120].replace("\n", " ")
            else:
                preview = chunk.text[:120].replace("\n", " ")
            lines.append(f"{idx}. {chapter_name}: {preview}...")
        return "\n".join(lines)
