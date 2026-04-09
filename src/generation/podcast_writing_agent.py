import os
import re
import json
from pathlib import Path
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.generation.manuscript import PodcastManuscript, ChapterManuscript
from src.generation.writing_state import WritingState, WritingPhase
from src.core.prompts import PLANNING_PROMPT, CHAPTER_WRITING_PROMPT, POLISH_PROMPT
from src.core.node_generator import create_llm
from src.logging_config import logger


class PodcastWritingAgent:
    """
    Autonomous agent that generates "聊一聊" style podcast manuscripts
    from NarrativeNode index + original Chunk text.

    Workflow:
      Phase 1 (Planning): Analyze all nodes → create outline + state
      Phase 2 (Writing): Process chunks sequentially → write chapter manuscripts
      Phase 3 (Polish): Merge + polish all chapters → final manuscript
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        output_dir: str = "output",
    ):
        self.api_key = api_key
        self.model = model
        self.output_dir = Path(output_dir)
        self.llm = create_llm(api_key=api_key, model=model, temperature=0.7)
        self.state: Optional[WritingState] = None
        self.plan: Optional[dict] = None
        self.chunks: list[Chunk] = []
        self.all_nodes: list[NarrativeNode] = []

    # === Public API ===

    async def run(self, chunks: list[Chunk], nodes: list[NarrativeNode], title: str) -> PodcastManuscript:
        """
        Main entry point. Run all three phases.
        """
        self.chunks = chunks
        self.all_nodes = nodes
        self._init_state(title)

        # Phase 1: Planning
        await self._phase1_planning()

        # Phase 2: Write by chunk
        await self._phase2_write()

        # Phase 3: Polish
        manuscript = await self._phase3_polish()

        return manuscript

    # === Phase 1: Planning ===

    async def _phase1_planning(self):
        """Read all nodes, create outline, save to state."""
        logger.info("Phase 1: Planning...")
        self.state.phase = WritingPhase.PLANNING

        nodes_summary = self._build_nodes_summary(self.all_nodes)
        prompt = PLANNING_PROMPT.format(nodes_summary=nodes_summary)

        messages = [
            SystemMessage(content="你是一个资深播客策划师，输出纯JSON。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content.strip()
        # Try to extract JSON from markdown code blocks first
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        try:
            plan_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to find any JSON object in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group(0))
            else:
                raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")

        self.plan = plan_data
        self.state.outline = plan_data
        self.state.phase = WritingPhase.WRITING
        self._save_state()

    # === Phase 2: Write by chunk ===

    async def _phase2_write(self):
        """Process chunks sequentially, write chapter manuscript for each."""
        logger.info("Phase 2: Writing chapters...")
        self.state.phase = WritingPhase.WRITING

        # Build nodes-per-chunk lookup
        nodes_by_chunk = {}
        for node in self.all_nodes:
            cid = node.parent_chunk_id
            if cid not in nodes_by_chunk:
                nodes_by_chunk[cid] = []
            nodes_by_chunk[cid].append(node)

        for i, chunk in enumerate(self.chunks):
            # Resume: skip already-written chunks
            if i < self.state.current_chunk_index:
                continue

            chunk_nodes = nodes_by_chunk.get(chunk.id, [])
            if not chunk_nodes:
                continue

            chapter_info = self._get_chapter_info(i, chunk, self.plan)
            manuscript_text = await self._write_chapter(chunk, chunk_nodes, chapter_info)

            self.state.add_chapter(chunk.id, manuscript_text)
            self.state.current_chunk_index += 1
            self._save_state()

            logger.info(f"  Chunk {i+1}/{len(self.chunks)} done: {chapter_info['title']}")

        self.state.phase = WritingPhase.POLISHING
        self._save_state()

    async def _write_chapter(
        self,
        chunk: Chunk,
        nodes: list[NarrativeNode],
        chapter_info: dict
    ) -> str:
        """Generate manuscript for a single chapter."""
        nodes_summary = self._build_nodes_summary(nodes)
        established = self._format_established_claims(self.state.established_claims)
        core_themes = ", ".join(self.plan.get("core_themes", []))

        prompt = CHAPTER_WRITING_PROMPT.format(
            chapter_title=chapter_info["title"],
            chapter_summary=chapter_info["summary"],
            core_themes=core_themes,
            established_claims=established,
            nodes_summary=nodes_summary,
            chunk_text=chunk.text[:8000],
        )

        messages = [
            SystemMessage(content="你是一个播客主播，输出纯文本稿子，不要JSON。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")
        return response.content.strip()

    # === Phase 3: Polish ===

    async def _phase3_polish(self) -> PodcastManuscript:
        """Polish all written chapters and produce final manuscript."""
        logger.info("Phase 3: Polishing...")
        self.state.phase = WritingPhase.POLISHING

        full = "\n\n---\n\n".join([
            ch.manuscript for ch in self.state.written_chapters
        ])

        prompt = POLISH_PROMPT.format(full_manuscript=full)

        messages = [
            SystemMessage(content="你是一个播客稿编辑，输出纯文本。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")
        polished = response.content.strip()

        chapters = [
            ChapterManuscript(chunk_id=ch.chunk_id, title=self._get_chapter_title_by_id(ch.chunk_id), manuscript=ch.manuscript)
            for ch in self.state.written_chapters
        ]

        manuscript = PodcastManuscript(
            title=self.state.book_title,
            chapters=chapters,
            full_manuscript=polished,
        )

        self._save_output(polished)

        self.state.phase = WritingPhase.DONE
        self._save_state()

        return manuscript

    # === Helpers ===

    def _init_state(self, title: str):
        state_path = self._get_state_path(title)
        if state_path.exists():
            self.state = WritingState.load(state_path)
            logger.info(f"Resumed from checkpoint: phase={self.state.phase}, chunk={self.state.current_chunk_index}")
        else:
            self.state = WritingState(book_title=title)

    def _get_state_path(self, title: str) -> Path:
        safe = re.sub(r'[<>:"/\\|?*]', '_', title)
        return self.output_dir / safe / "writing_state.json"

    def _save_state(self):
        if self.state:
            try:
                self.state.save(self._get_state_path(self.state.book_title))
            except Exception as e:
                logger.warning(f"Failed to save state: {e}")

    def _save_output(self, full_manuscript: str):
        safe = re.sub(r'[<>:"/\\|?*]', '_', self.state.book_title)
        out_dir = self.output_dir / safe
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "manuscript.txt").write_text(full_manuscript, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save output: {e}")

    def _build_nodes_summary(self, nodes: list[NarrativeNode]) -> str:
        """Format NarrativeNode list as readable summary for prompts."""
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if hasattr(n, 'characters') else "无"
            lines.append(
                f"节点{i+1}: [{n.narrative_role}] {n.scene}\n"
                f"  情境: {n.situation}\n"
                f"  转折: {n.turning_point}\n"
                f"  情绪弧: {n.emotional_arc}\n"
                f"  氛围: {n.mood_tone} | 节奏: {n.narrative_rhythm}\n"
                f"  角色: {chars}"
            )
        return "\n\n".join(lines)

    def _format_established_claims(self, claims: list[str]) -> str:
        if not claims:
            return "（无，上文暂无已确立观点）"
        return "；".join([f"{i+1}. {c}" for i, c in enumerate(claims)])

    def _get_chapter_info(self, index: int, chunk: Chunk, plan: dict) -> dict:
        """Get chapter title/summary from plan, fallback to chunk.chapter."""
        if plan and "chapters" in plan:
            for ch in plan["chapters"]:
                if ch["chunk_id"] == chunk.id:
                    return ch
        return {
            "chunk_id": chunk.id,
            "title": chunk.chapter or f"第{index+1}章",
            "summary": f"章节{index+1}，约{len(chunk.text)}字"
        }

    def _get_chapter_title_by_id(self, chunk_id: str) -> str:
        if self.plan and "chapters" in self.plan:
            for ch in self.plan["chapters"]:
                if ch["chunk_id"] == chunk_id:
                    return ch["title"]
        return chunk_id
