# Podcast Writing Agent Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an autonomous PodcastWritingAgent that generates "聊一聊" style podcast manuscripts from NarrativeNode index + original Chunk text.

**Architecture:** Three-phase agent (Planning → Write-by-Chunk → Polish). State persisted to JSON file for checkpoint/resume. No vector retrieval during writing.

**Tech Stack:** Python, LangChain ChatOpenAI, Pydantic, JSON state file.

---

## File Map

```
src/generation/
  manuscript.py              # PodcastManuscript output model
  podcast_writing_agent.py   # Main agent (Phase 1+2+3 + state management)
  prompts.py                 # Add: PLANNING_PROMPT, CHAPTER_WRITING_PROMPT, POLISH_PROMPT

src/models/
  manuscript.py              # Move/alias PodcastManuscript here? No — keep in generation/

src/storage/
  database.py                # Already saves nodes/chunks — check if we need new table

tests/generation/
  test_podcast_writing_agent.py
```

**Key existing files to reference:**
- `src/models/narrative_node.py` — NarrativeNode, CharacterState, RelationshipStateChange
- `src/models/chunk.py` — Chunk
- `src/core/node_generator.py` — `create_llm()` helper (reuse for agent)
- `src/generation/podcast_generator.py` — existing prompts for style reference
- `src/storage/database.py` — existing save/load patterns

---

## Chunk 1: PodcastManuscript Model

**Files:**
- Create: `src/generation/manuscript.py`
- Test: `tests/generation/test_manuscript.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_manuscript.py
import pytest
from src.generation.manuscript import PodcastManuscript, ChapterManuscript

def test_podcast_manuscript_creation():
    manuscript = PodcastManuscript(
        title="神的九十亿个名字",
        author="阿瑟·克拉克",
        chapters=[
            ChapterManuscript(
                chunk_id="chunk-0001",
                title="引言",
                manuscript="哈喽，大家好..."
            )
        ]
    )
    assert manuscript.title == "神的九十亿个名字"
    assert len(manuscript.chapters) == 1
    assert "哈喽" in manuscript.full_manuscript

def test_full_manuscript_concatenation():
    manuscript = PodcastManuscript(
        title="Test",
        author="Author",
        chapters=[
            ChapterManuscript(chunk_id="c1", title="第1章", manuscript="第一章内容"),
            ChapterManuscript(chunk_id="c2", title="第2章", manuscript="第二章内容"),
        ]
    )
    assert "第一章内容" in manuscript.full_manuscript
    assert "第二章内容" in manuscript.full_manuscript
    # Should have chapter separator
    assert "第1章" in manuscript.full_manuscript
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_manuscript.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# src/generation/manuscript.py
from pydantic import BaseModel
from typing import Optional


class ChapterManuscript(BaseModel):
    """Single chapter of a podcast manuscript."""
    chunk_id: str
    title: str
    manuscript: str  # full chapter text


class PodcastManuscript(BaseModel):
    """Complete podcast manuscript."""
    title: str
    author: str = ""
    estimated_duration: str = ""  # e.g., "25分钟"
    chapters: list[ChapterManuscript] = []

    @property
    def full_manuscript(self) -> str:
        """Merge all chapter manuscripts with separators."""
        parts = []
        for i, ch in enumerate(self.chapters, 1):
            parts.append(f"第{i}章：{ch.title}\n\n{ch.manuscript}")
        return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_manuscript.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/manuscript.py tests/generation/test_manuscript.py
git commit -m "feat: add PodcastManuscript model"
```

---

## Chunk 2: WritingState Model

**Files:**
- Create: `src/generation/writing_state.py`
- Test: `tests/generation/test_writing_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_writing_state.py
import pytest
import json
import tempfile
from pathlib import Path
from src.generation.writing_state import WritingState, WritingPhase

def test_state_initialization():
    state = WritingState(book_title="Test Book")
    assert state.phase == WritingPhase.PLANNING
    assert state.current_chunk_index == 0
    assert len(state.written_chapters) == 0
    assert len(state.established_claims) == 0

def test_state_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "state.json"
        state = WritingState(book_title="Test Book")
        state.current_chunk_index = 2
        state.established_claims.append("克拉克是宇宙诗人")
        state.save(path)

        loaded = WritingState.load(path)
        assert loaded.current_chunk_index == 2
        assert "克拉克是宇宙诗人" in loaded.established_claims
        assert loaded.book_title == "Test Book"

def test_state_update_after_chapter():
    state = WritingState(book_title="Test")
    state.phase = WritingPhase.WRITING
    state.current_chunk_index = 0
    state.add_chapter("chunk-0001", "引言", "这是稿子...")
    assert len(state.written_chapters) == 1
    assert state.current_chunk_index == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_writing_state.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# src/generation/writing_state.py
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import json
from pathlib import Path


class WritingPhase(str, Enum):
    PLANNING = "planning"
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"


class ChapterOutline(BaseModel):
    chunk_id: str
    title: str
    summary: str = ""


class WrittenChapter(BaseModel):
    chunk_id: str
    manuscript: str


class WritingState(BaseModel):
    """State file for PodcastWritingAgent checkpoint/resume."""
    book_title: str
    phase: WritingPhase = WritingPhase.PLANNING
    current_chunk_index: int = 0

    # Phase 1 output
    outline: Optional[dict] = None  # {"chapters": [...], "overall_tone": "...", "core_themes": [...]}

    # Phase 2 output
    written_chapters: list[WrittenChapter] = Field(default_factory=list)
    established_claims: list[str] = Field(default_factory=list)

    def add_chapter(self, chunk_id: str, manuscript: str):
        self.written_chapters.append(WrittenChapter(chunk_id=chunk_id, manuscript=manuscript))
        # NOTE: caller is responsible for incrementing current_chunk_index

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "WritingState":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_writing_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/writing_state.py tests/generation/test_writing_state.py
git commit -m "feat: add WritingState model for checkpoint management"
```

---

## Chunk 3: Prompts for All Three Phases

**Files:**
- Modify: `src/core/prompts.py`

Add three new prompts at the end of `src/core/prompts.py`:

- [ ] **Step 1: Read existing prompts.py to find insertion point**

Run: `wc -l src/core/prompts.py`

- [ ] **Step 2: Add new prompts to prompts.py**

Append these three prompts:

```python
# At end of src/core/prompts.py, add:

PLANNING_PROMPT = """你是一个资深播客策划师。你的任务是从一部小说的叙事节点索引中提取结构信息，用于规划播客节目的章节划分。

## 叙事节点索引说明
每个叙事节点包含：
- scene: 场景（时间+地点）
- situation: 核心情境（1句话）
- turning_point: 转折点
- emotional_arc: 情绪弧
- narrative_role: 叙事角色（opening/rising/climax/ending）
- characters: 在场角色列表

## 你的任务

分析全部叙事节点后，输出一个 JSON 结构：

```json
{
  "chapters": [
    {
      "chunk_id": "chunk-0001",
      "title": "章节标题（简洁，10字以内）",
      "summary": "这个章节要讲什么（1-2句话）"
    }
  ],
  "overall_tone": "播客整体基调描述（3-5句话）",
  "core_themes": ["核心主题1", "核心主题2", "核心主题3"]
}
```

## 注意事项

- chapters 数量不代表叙事节点数量，而是播客"章"的数量
- 相邻的同类叙事节点可以合并为一章
- overall_tone 要体现播客风格（如"带有敬畏感的理性探讨"）
- core_themes 是贯穿全书的核心观点，后面章节要呼应

## 叙事节点列表：
{nodes_summary}
"""


CHAPTER_WRITING_PROMPT = """你是一个播客主播，正在录制一期"聊一聊"风格的节目。

## 写作风格要求
- 口语化，像在跟朋友聊天
- 先聊情节（用 NarrativeNode 索引作为骨架），再穿插个人思考
- 可以从原文提取生动细节作为"聊"的素材，但不要大段朗读原文
- 适当使用口头禅（如"是吧"、"怎么说呢"、"你像"）
- 每个章节要有自然的过渡句，承接上文引出下文
- 在章节后半段加入"个人思考"——这个情节为什么重要、折射出什么

## 本章基本信息
- 章节标题：{chapter_title}
- 章节摘要：{chapter_summary}
- 全书核心主题：{core_themes}
- 上文已确立的观点（不要重复，要承接）：{established_claims}

## 本章叙事节点（播客讲述骨架）
{nodes_summary}

## 本章完整原文（参考素材，不要大段朗读）
```原文
{chunk_text}
```

## 输出格式
直接输出一章的播客稿，不要前缀说明，不要章节标题（已在基本信息中给出），直接开始聊。
"""


POLISH_PROMPT = """你是一个播客稿编辑。你的任务是对多章节播客稿进行全局润色。

## 润色要求

1. **消除重复**：各章节间可能重复的观点、表述要合并/删除
2. **统一语气**：确保口语化风格一致，没有书面语残留
3. **强化过渡**：检查章与章之间的过渡句是否自然
4. **升华结尾**：最后一章的结尾要有力量感，适当呼应全书主题
5. **个人思考**：确保每个章节都有个人思考，不是纯情节复述

## 全文稿子
---
{full_manuscript}
---

## 输出
直接输出润色后的完整稿子，不要说明改了哪里。
"""
```

- [ ] **Step 3: Run tests to ensure nothing broke**

Run: `pytest tests/core/test_node_generator.py tests/generation/test_podcast_generator.py -v`
Expected: PASS (no changes to existing code, just addition)

- [ ] **Step 4: Commit**

```bash
git add src/core/prompts.py
git commit -m "feat: add PLANNING_PROMPT, CHAPTER_WRITING_PROMPT, POLISH_PROMPT"
```

---

## Chunk 4: PodcastWritingAgent (Core Logic)

**Files:**
- Create: `src/generation/podcast_writing_agent.py`
- Test: `tests/generation/test_podcast_writing_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/generation/test_podcast_writing_agent.py
import pytest
import json
import tempfile
from pathlib import Path
from src.generation.podcast_writing_agent import PodcastWritingAgent
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState

def make_nodes(chunk_id: str, count: int) -> list[NarrativeNode]:
    return [
        NarrativeNode(
            id=f"{chunk_id}-n{i}",
            parent_chunk_id=chunk_id,
            beat_index=i,
            scene=f"场景{i}",
            situation=f"情境{i}",
            turning_point=f"转折{i}",
            emotional_arc=f"情绪{i}",
            mood_tone="平静",
            narrative_rhythm="steady",
            narrative_role="rising"
        )
        for i in range(count)
    ]

def test_agent_init():
    agent = PodcastWritingAgent(api_key="test-key")
    assert agent.state is None
    assert agent.plan is None

def test_build_nodes_summary():
    """Test that _build_nodes_summary formats NarrativeNodes correctly."""
    agent = PodcastWritingAgent(api_key="test-key")
    nodes = make_nodes("chunk-0001", 2)
    # Test the formatting helper works
    summary = agent._build_nodes_summary(nodes)
    assert "场景0" in summary
    assert "情境0" in summary
    assert "转折0" in summary

def test_state_path_generation():
    """Test output path for state file."""
    agent = PodcastWritingAgent(api_key="test-key")
    path = agent._get_state_path("神的九十亿个名字")
    assert "神的九十亿个名字" in str(path)
    assert path.name == "writing_state.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_podcast_writing_agent.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation skeleton**

```python
# src/generation/podcast_writing_agent.py
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
        plan_data = json.loads(response.content.strip())

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
                # Skip chunks with no narrative nodes
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
            chunk_text=chunk.text[:8000],  # Truncate very long chunks
        )

        messages = [
            SystemMessage(content="你是一个播客主播，输出纯文本稿子，不要JSON。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    # === Phase 3: Polish ===

    async def _phase3_polish(self) -> PodcastManuscript:
        """Polish all written chapters and produce final manuscript."""
        logger.info("Phase 3: Polishing...")
        self.state.phase = WritingPhase.POLISHING

        # Build full manuscript for polishing
        full = "\n\n---\n\n".join([
            ch.manuscript for ch in self.state.written_chapters
        ])

        prompt = POLISH_PROMPT.format(full_manuscript=full)

        messages = [
            SystemMessage(content="你是一个播客稿编辑，输出纯文本。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        polished = response.content.strip()

        # Build final manuscript
        chapters = [
            ChapterManuscript(chunk_id=ch.chunk_id, title=self._get_chapter_title_by_id(ch.chunk_id), manuscript=ch.manuscript)
            for ch in self.state.written_chapters
        ]

        manuscript = PodcastManuscript(
            title=self.state.book_title,
            chapters=chapters,
        )

        # Save output
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
            self.state.save(self._get_state_path(self.state.book_title))

    def _save_output(self, full_manuscript: str):
        safe = re.sub(r'[<>:"/\\|?*]', '_', self.state.book_title)
        out_dir = self.output_dir / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript.txt").write_text(full_manuscript, encoding="utf-8")

    def _build_nodes_summary(self, nodes: list[NarrativeNode]) -> str:
        """Format NarrativeNode list as readable summary for prompts."""
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) or "无"
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
        # Fallback
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_podcast_writing_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/podcast_writing_agent.py tests/generation/test_podcast_writing_agent.py
git commit -m "feat: add PodcastWritingAgent with 3-phase workflow"
```

---

## Chunk 5: Integration with Pipeline

**Files:**
- Modify: `src/pipeline.py`

- [ ] **Step 1: Add run method to pipeline**

Add to `NovelToPodcastPipeline`:

```python
async def run_writing_agent(self, chunks: list[Chunk], nodes: list[NarrativeNode], title: str):
    """Run the podcast writing agent after nodes are generated."""
    from src.generation.podcast_writing_agent import PodcastWritingAgent
    agent = PodcastWritingAgent(
        api_key=self.api_key,
        model=self.model,
    )
    return await agent.run(chunks, nodes, title)
```

- [ ] **Step 2: Add convenience method on pipeline**

Add to `NovelToPodcastPipeline`:

```python
async def process_full(self, book_path: str):
    """Run the full pipeline: book → chunks → nodes → podcast manuscript."""
    from src.utils.book_adapter import read_book

    reader = read_book(book_path)
    text = reader.read()

    # Existing: chunk + generate nodes
    chunks = self.chunker.chunk(text)
    all_nodes = []
    for chunk in chunks:
        nodes = await self.node_generator.generate_from_chunk(chunk)
        if not isinstance(nodes, list):
            nodes = [nodes]
        all_nodes.extend(nodes)

    # New: write podcast manuscript
    manuscript = await self.run_writing_agent(chunks, all_nodes, reader.title)

    return manuscript
```

- [ ] **Step 3: Test that pipeline still passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/pipeline.py
git commit -m "feat: add run_writing_agent and process_full to pipeline"
```

---

## Chunk 6: Full Integration Test (Optional/E2E)

**Files:**
- Create: `tests/generation/test_e2e_writing_agent.py`

- [ ] **Step 1: Write a minimal E2E test with mocked LLM**

```python
# tests/generation/test_e2e_writing_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from src.generation.podcast_writing_agent import PodcastWritingAgent
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState

def test_e2e_agent_with_mocked_llm():
    """End-to-end test with mocked LLM responses."""
    chunks = [
        Chunk(id="chunk-0001", text="今天妈妈死了。", order=0, chapter="第一部 Ⅰ"),
        Chunk(id="chunk-0002", text="第二天醒来是周六。", order=1, chapter="第一部 Ⅱ"),
    ]
    nodes = [
        NarrativeNode(
            id="n-0-0", parent_chunk_id="chunk-0001", beat_index=0,
            scene="养老院",
            situation="默尔索收到母亲去世的电报",
            turning_point="他不确定母亲去世的时间",
            emotional_arc="默尔索从漠然到微妙的困惑",
            mood_tone="疏离, 冷漠", narrative_rhythm="slow",
            narrative_role="opening",
            characters=[CharacterState(name="默尔索", state_before="漠然")]
        ),
        NarrativeNode(
            id="n-1-0", parent_chunk_id="chunk-0002", beat_index=0,
            scene="公寓",
            situation="默尔索醒来发现是周六",
            turning_point="想起老板对他请假的不满",
            emotional_arc="默尔索从困惑到接受",
            mood_tone="平静", narrative_rhythm="steady",
            narrative_role="rising",
            characters=[CharacterState(name="默尔索", state_before="困惑")]
        ),
    ]

    # Mock the LLM responses
    agent = PodcastWritingAgent(api_key="fake")

    # Mock planning phase
    with patch.object(agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.side_effect = [
            # Phase 1: planning
            type('R', (), {'content': '{"chapters":[{"chunk_id":"chunk-0001","title":"开场","summary":"默尔索母亲去世"},{"chunk_id":"chunk-0002","title":"周六","summary":"默尔索的日常"}],"overall_tone":"疏离冷漠","core_themes":["存在主义","社会规则"]}'})(),
            # Phase 2: chapter 1
            type('R', (), {'content': '这是第一章的播客稿...'})(),
            # Phase 2: chapter 2
            type('R', (), {'content': '这是第二章的播客稿...'})(),
            # Phase 3: polish
            type('R', (), {'content': '润色后的完整稿子。'})(),
        ]

        import asyncio
        manuscript = asyncio.run(agent.run(chunks, nodes, "局外人"))

        assert manuscript is not None
        assert len(manuscript.chapters) == 2
        assert "润色后的完整稿子" in manuscript.full_manuscript
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/generation/test_e2e_writing_agent.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/generation/test_e2e_writing_agent.py
git commit -m "test: add e2e test for PodcastWritingAgent with mocked LLM"
```

---

## Dependency Order

Chunks must be implemented in order:
1. `manuscript.py` (output model)
2. `writing_state.py` (checkpoint model)
3. Prompts (just append to `prompts.py`)
4. `podcast_writing_agent.py` (uses above + prompts)
5. Pipeline integration
6. E2E test
