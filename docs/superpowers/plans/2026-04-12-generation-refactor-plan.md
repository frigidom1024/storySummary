# Generation 包重构实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 `src/generation/` 包，提供统一入口 `ManuscriptPipeline`，单草稿模式，支持断点恢复

**Architecture:** Pipeline 风格，三阶段流程（PREPARE → WRITING → POLISHING），单 draft 贯穿全程，AI 可随时修改草稿

**Tech Stack:** Python 3.11+, pydantic, langchain-openai, asyncio

---

## Chunk 1: models.py + state.py

**Files:**
- Create: `src/generation/models.py`
- Create: `src/generation/state.py`
- Test: `tests/generation/test_models.py`, `tests/generation/test_state.py`

### models.py

```python
from pydantic import BaseModel
from typing import Optional


class ManuscriptResult(BaseModel):
    """生成结果"""
    title: str
    draft: str
    phase: str
    chapters_written: int
    total_chunks: int
```

### state.py

```python
import json
import re
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class WritingPhase(str, Enum):
    PREPARE = "prepare"
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"


class WritingState(BaseModel):
    """断点状态"""
    book_id: str
    book_title: str
    phase: WritingPhase = WritingPhase.PREPARE
    current_chunk_index: int = 0
    draft: str = ""
    outline: Optional[dict] = None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "WritingState":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @classmethod
    def get_state_path(cls, book_id: str, output_dir: str, book_title: str) -> Path:
        safe = re.sub(r'[<>:"/\\|?*]', '_', book_title)
        return Path(output_dir) / safe / "writing_state.json"
```

- [ ] **Step 1: Write failing tests**

```python
# tests/generation/test_models.py
def test_manuscript_result():
    result = ManuscriptResult(title="Test", draft="", phase="done", chapters_written=1, total_chunks=2)
    assert result.title == "Test"

# tests/generation/test_state.py
def test_writing_state_default():
    state = WritingState(book_id="123", book_title="Test Book")
    assert state.phase == WritingPhase.PREPARE
    assert state.current_chunk_index == 0
    assert state.draft == ""

def test_writing_state_save_load(tmp_path):
    state = WritingState(book_id="123", book_title="Test Book", draft="hello")
    path = tmp_path / "state.json"
    state.save(path)
    loaded = WritingState.load(path)
    assert loaded.draft == "hello"
    assert loaded.book_id == "123"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/generation/test_models.py tests/generation/test_state.py -v`
Expected: FAIL - files/modules not found

- [ ] **Step 3: Create src/generation/ directory and files**

Create `src/generation/__init__.py`, `src/generation/models.py`, `src/generation/state.py`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/generation/test_models.py tests/generation/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/models.py src/generation/state.py src/generation/__init__.py
git commit -m "feat(generation): add models.py and state.py"
```

---

## Chunk 2: context.py

**Files:**
- Create: `src/generation/context.py`
- Test: `tests/generation/test_context.py`

### context.py

```python
from src.models.narrative_node import NarrativeNode


class WritingContext:
    """对话上下文，维护草稿摘要和 AI 记忆"""

    def __init__(self):
        self.draft: str = ""
        self.context_summary: str = ""
        self.established_facts: list[str] = []

    def build_prompt_context(self, chunk, nodes: list[NarrativeNode]) -> str:
        """生成 AI 提示词上下文"""
        parts = []

        if self.context_summary:
            parts.append(f"【已写内容摘要】\n{self.context_summary}\n")

        if nodes:
            nodes_text = self._format_nodes(nodes)
            parts.append(f"【本章叙事节点】\n{nodes_text}\n")

        return "\n".join(parts)

    def update_draft(self, new_draft: str) -> None:
        """更新草稿（AI 可能修改了之前的内容）"""
        self.draft = new_draft
        self._update_summary()

    def append_chapter(self, chapter_text: str) -> None:
        """追加新章节到草稿"""
        if self.draft:
            self.draft += "\n\n---\n\n" + chapter_text
        else:
            self.draft = chapter_text
        self._update_summary()

    def _update_summary(self) -> None:
        """更新上下文摘要（截取前 500 字）"""
        self.context_summary = self.draft[:500] if self.draft else ""

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if n.characters else "无"
            lines.append(
                f"节点{i+1}: [{n.narrative_role}] {n.scene}\n"
                f"  情境: {n.situation}\n"
                f"  角色: {chars}"
            )
        return "\n".join(lines)
```

- [ ] **Step 1: Write failing test**

```python
# tests/generation/test_context.py
def test_writing_context_initial_state():
    ctx = WritingContext()
    assert ctx.draft == ""
    assert ctx.context_summary == ""

def test_writing_context_append():
    ctx = WritingContext()
    ctx.append_chapter("第一章内容")
    assert ctx.draft == "第一章内容"
    assert "第一章" in ctx.context_summary

def test_writing_context_build_prompt_context():
    ctx = WritingContext()
    ctx.append_chapter("已写内容摘要测试")
    # nodes = [] for simplicity
    prompt = ctx.build_prompt_context(chunk=None, nodes=[])
    assert "已写内容摘要" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_context.py -v`
Expected: FAIL

- [ ] **Step 3: Create context.py**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_context.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/context.py
git commit -m "feat(generation): add WritingContext"
```

---

## Chunk 3: writer.py

**Files:**
- Create: `src/generation/writer.py`
- Test: `tests/generation/test_writer.py`
- Reference: `src/core/prompts.py:223` (CHAPTER_WRITING_PROMPT)

### writer.py

```python
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.core.prompts import CHAPTER_WRITING_PROMPT
from src.core.node_generator import create_llm


class ChapterWriter:
    """单章生成器"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def write(
        self,
        chunk: Chunk,
        nodes: list[NarrativeNode],
        context_summary: str,
        draft_so_far: str,
    ) -> str:
        """
        生成单章播客稿
        AI 可以选择续写新章节，或修改 draft_so_far 中的旧内容
        返回: (new_draft, chapter_text) - 完整草稿和本章文本
        """
        nodes_summary = self._format_nodes(nodes)

        prompt = CHAPTER_WRITING_PROMPT.format(
            chapter_title=chunk.chapter or f"第{chunk.order + 1}章",
            chapter_summary=f"约{len(chunk.text)}字",
            core_themes="（待补充）",
            established_claims=context_summary or "（无）",
            nodes_summary=nodes_summary,
            chunk_text=chunk.text[:8000],
        )

        messages = [
            SystemMessage(content="你是一个播客主播，输出纯文本稿子。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")

        chapter_text = response.content.strip()

        # 追加到草稿
        if draft_so_far:
            new_draft = draft_so_far + "\n\n---\n\n" + chapter_text
        else:
            new_draft = chapter_text

        return new_draft, chapter_text

    def _format_nodes(self, nodes: list[NarrativeNode]) -> str:
        lines = []
        for i, n in enumerate(nodes):
            chars = ", ".join([c.name for c in n.characters]) if n.characters else "无"
            lines.append(
                f"节点{i+1}: [{n.narrative_role}] {n.scene}\n"
                f"  情境: {n.situation}\n"
                f"  转折: {n.turning_point or '无'}\n"
                f"  情绪弧: {n.emotional_arc or '无'} | 氛围: {n.mood_tone or '无'}\n"
                f"  角色: {chars}"
            )
        return "\n\n".join(lines)
```

- [ ] **Step 1: Write failing test** (mock LLM)

```python
# tests/generation/test_writer.py
from unittest.mock import AsyncMock, patch

def test_chapter_writer_format_nodes():
    writer = ChapterWriter()
    from src.models.narrative_node import NarrativeNode, CharacterState
    nodes = [
        NarrativeNode(
            id="n1",
            scene="川菜馆场景",
            situation="陈屿和方远在吃饭",
            narrative_role="rising",
            characters=[CharacterState(name="陈屿"), CharacterState(name="方远")],
        )
    ]
    result = writer._format_nodes(nodes)
    assert "川菜馆场景" in result
    assert "陈屿" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_writer.py -v`
Expected: FAIL

- [ ] **Step 3: Create writer.py**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_writer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/writer.py
git commit -m "feat(generation): add ChapterWriter"
```

---

## Chunk 4: polish.py

**Files:**
- Create: `src/generation/polish.py`
- Test: `tests/generation/test_polish.py`
- Reference: `src/core/prompts.py:252` (POLISH_PROMPT)

### polish.py

```python
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.prompts import POLISH_PROMPT
from src.core.node_generator import create_llm


class PolishPass:
    """润色器"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def polish(self, draft: str) -> str:
        """润色完整草稿"""
        prompt = POLISH_PROMPT.format(full_manuscript=draft)

        messages = [
            SystemMessage(content="你是一个播客稿编辑，输出纯文本。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")

        return response.content.strip()
```

- [ ] **Step 1: Write failing test**

```python
# tests/generation/test_polish.py
def test_polish_pass_init():
    polisher = PolishPass()
    assert polisher.api_key is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_polish.py -v`
Expected: FAIL

- [ ] **Step 3: Create polish.py**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_polish.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/polish.py
git commit -m "feat(generation): add PolishPass"
```

---

## Chunk 5: pipeline.py + __init__.py

**Files:**
- Create: `src/generation/pipeline.py`
- Modify: `src/generation/__init__.py`
- Test: `tests/generation/test_pipeline.py`

### pipeline.py

```python
import os
import re
from pathlib import Path
from typing import Optional

from src.models.narrative_node import NarrativeNode
from src.models.chunk import Chunk
from src.models.manuscript import ManuscriptResult
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
        if state.draft:
            context.draft = state.draft
            context._update_summary()

        while state.current_chunk_index < len(chunks):
            chunk = chunks[state.current_chunk_index]
            chunk_nodes = [n for n in nodes if n.parent_chunk_id == chunk.id]

            prompt_context = context.build_prompt_context(chunk, chunk_nodes)
            new_draft, _ = await self.writer.write(
                chunk=chunk,
                nodes=chunk_nodes,
                context_summary=prompt_context,
                draft_so_far=context.draft,
            )

            context.update_draft(new_draft)
            state.draft = context.draft
            state.current_chunk_index += 1
            state.save(state_path)

        # 6. [POLISHING] 阶段
        state.phase = WritingPhase.POLISHING
        state.save(state_path)

        polished = await self.polisher.polish(context.draft)

        # 7. 保存最终稿
        safe = re.sub(r'[<>:"/\\|?*]', '_', book.title)
        out_dir = Path(self.output_dir) / safe
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript.txt").write_text(polished, encoding="utf-8")

        state.phase = WritingPhase.DONE
        state.save(state_path)

        return ManuscriptResult(
            title=book.title,
            draft=polished,
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
```

### __init__.py

```python
from src.generation.pipeline import ManuscriptPipeline
from src.generation.models import ManuscriptResult
from src.generation.state import WritingState, WritingPhase

__all__ = ["ManuscriptPipeline", "ManuscriptResult", "WritingState", "WritingPhase"]
```

- [ ] **Step 1: Write failing test** (mock dependencies)

```python
# tests/generation/test_pipeline.py
def test_manuscript_pipeline_init():
    pipeline = ManuscriptPipeline()
    assert pipeline.output_dir == "output"
    assert pipeline.writer is not None
    assert pipeline.polisher is not None

def test_load_chunks():
    # 需要实际数据或 mock
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/generation/test_pipeline.py -v`
Expected: FAIL

- [ ] **Step 3: Create pipeline.py**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/generation/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generation/pipeline.py src/generation/__init__.py
git commit -m "feat(generation): add ManuscriptPipeline"
```

---

## 集成测试

- [ ] **创建 tests/generation/__init__.py**
- [ ] **运行完整测试套件**

Run: `pytest tests/generation/ -v`

- [ ] **手动测试（使用已有数据）**

```python
import asyncio
from src.generation import ManuscriptPipeline

async def test():
    pipeline = ManuscriptPipeline()
    # 使用已有 book_id
    result = await pipeline.run("3b977938-aa61-4cee-b03e-889acd0ef873")
    print(result.title, result.phase, len(result.draft))

asyncio.run(test())
```

---

## 清理旧文件

后续（不在本次计划内）可删除：
- `src/generation/podcast_writing_agent.py`（旧）
- `src/generation/podcast_generator.py`（旧）
- `src/generation/manuscript.py`（将被 models.py 替代）
- `src/generation/writing_state.py`（将被 state.py 替代）
