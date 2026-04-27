# src/generation 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重组 `src/generation/` 包，将 LLM agent 移入 `agents/` 子包，修复引用错误，清理 dead code。

**Architecture:** 创建 `agents/` 子包收纳所有 LLM agent（outline, style, writer, polish），保留 `models.py`、`state.py`、`pipeline.py`、`research_tools.py` 在根目录作为基础设施层。

**Tech Stack:** Python 文件移动 + import 路径更新

---

## 任务总览

| Task | 描述 |
|------|------|
| 1 | 创建 agents/ 目录和 __init__.py |
| 2 | 移动 outline_agent.py → agents/outline.py |
| 3 | 移动 style_agent.py → agents/style.py |
| 4 | 移动 writer.py → agents/writer.py + 修复 StoryContext 引用 |
| 5 | 移动 polish.py → agents/polish.py |
| 6 | 更新 pipeline.py 的 import 和清理 dead code |
| 7 | 更新根目录 __init__.py 导出 |
| 8 | 验证无 import 错误 |

---

## Task 1: 创建 agents/ 目录结构

**Files:**
- Create: `src/generation/agents/__init__.py`

- [ ] **Step 1: 创建目录和 __init__.py**

```python
"""LLM Agents for manuscript generation."""

from .outline import OutlineAgent
from .style import StyleLearningAgent
from .writer import ChapterWriter
from .polish import PolishAgent

__all__ = [
    "OutlineAgent",
    "StyleLearningAgent",
    "ChapterWriter",
    "PolishAgent",
]
```

Run: 不需要运行，创建文件即可

- [ ] **Step 2: 提交**

```bash
git add src/generation/agents/__init__.py
git commit -m "feat(generation): create agents package"
```

---

## Task 2: 移动 outline_agent.py → agents/outline.py

**Files:**
- Create: `src/generation/agents/outline.py`
- Delete: `src/generation/outline_agent.py`

- [ ] **Step 1: 读取原文件**

文件: `src/generation/outline_agent.py`（已读过，内容如下）

```python
import os
from collections.abc import Callable

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
from src.generation.research_tools import ManuscriptResearchToolkit
from src.logging_config import debug
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode


class OutlineAgent:
    """负责生成全书级 outline（含伏笔与锚点）。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.3)

    async def build_outline(
        self,
        book_id: str,
        chunks: list[Chunk],
        nodes: list[NarrativeNode],
        progress_callback: Callable[[str], None] | None = None,
    ) -> str:
        # ... (完整代码见原文件)
```

- [ ] **Step 2: 创建新文件**

内容：复制 `src/generation/outline_agent.py` 完整内容到 `src/generation/agents/outline.py`，不做任何修改。

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/agents/outline.py`
Expected: 无输出（成功）

- [ ] **Step 4: 删除原文件**

Run: `rm src/generation/outline_agent.py`

- [ ] **Step 5: 提交**

```bash
git add src/generation/agents/outline.py
git rm src/generation/outline_agent.py
git commit -m "refactor(generation): move OutlineAgent to agents/outline.py"
```

---

## Task 3: 移动 style_agent.py → agents/style.py

**Files:**
- Create: `src/generation/agents/style.py`
- Delete: `src/generation/style_agent.py`

- [ ] **Step 1: 读取原文件**

文件: `src/generation/style_agent.py`（已读过，内容如下）

```python
import os

from langchain.agents import create_agent

from src.core.node_generator import create_llm
from src.logging_config import debug


class StyleLearningAgent:
    """从参考口播稿提炼可复用的抽象风格画像。"""
    # ... (完整代码见原文件)
```

- [ ] **Step 2: 创建新文件**

内容：复制 `src/generation/style_agent.py` 完整内容到 `src/generation/agents/style.py`，不做任何修改。

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/agents/style.py`
Expected: 无输出（成功）

- [ ] **Step 4: 删除原文件**

Run: `rm src/generation/style_agent.py`

- [ ] **Step 5: 提交**

```bash
git add src/generation/agents/style.py
git rm src/generation/style_agent.py
git commit -m "refactor(generation): move StyleLearningAgent to agents/style.py"
```

---

## Task 4: 移动 writer.py → agents/writer.py + 修复 StoryContext 引用

**Files:**
- Create: `src/generation/agents/writer.py`
- Delete: `src/generation/writer.py`

- [ ] **Step 1: 分析 writer.py 中的问题**

原文件 `src/generation/writer.py` 第 36-37 行有：
```python
nodes_text = self._format_nodes(nodes)
memory_text = StoryContext.build_memory(completed_drafts)  # ← 不存在！
last_draft = completed_drafts[-1].chapter_text if completed_drafts else "（无）"
```

`StoryContext.build_memory` 不存在，需要：
1. 移除 `memory_text` 变量
2. 从 `user_prompt` 中移除 `{memory_text}` 引用

- [ ] **Step 2: 创建修复后的 writer.py**

内容来自原 `src/generation/writer.py`，修改点：

1. 移除第 36 行的 `memory_text = StoryContext.build_memory(completed_drafts)`
2. 移除 `user_prompt` 中的 `## 已完成草稿记忆\n{memory_text}` 块（第 54-60 行）

修改后的 `user_prompt` 构建（第 47-73 行）：
```python
user_prompt = f"""
## 紧邻前文章节尾部（用于衔接语气）
```上章
{last_draft}
```

## 当前章节
- 标题: {chapter_title}
- 原文长度: {len(chunk.text)} 字

## 当前章节节点索引
{nodes_text}

## 当前章节完整原文
```原文
{chunk.text}
```
"""
```

（移除了 `## 已完成草稿记忆` 整个块）

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/agents/writer.py`
Expected: 无输出（成功）

- [ ] **Step 4: 删除原文件**

Run: `rm src/generation/writer.py`

- [ ] **Step 5: 提交**

```bash
git add src/generation/agents/writer.py
git rm src/generation/writer.py
git commit -m "refactor(generation): move ChapterWriter to agents/writer.py and fix StoryContext reference"
```

---

## Task 5: 移动 polish.py → agents/polish.py

**Files:**
- Create: `src/generation/agents/polish.py`
- Delete: `src/generation/polish.py`

- [ ] **Step 1: 读取原文件**

文件: `src/generation/polish.py`（已读过）

- [ ] **Step 2: 创建新文件**

内容：复制 `src/generation/polish.py` 完整内容到 `src/generation/agents/polish.py`，不做任何修改。

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/agents/polish.py`
Expected: 无输出（成功）

- [ ] **Step 4: 删除原文件**

Run: `rm src/generation/polish.py`

- [ ] **Step 5: 提交**

```bash
git add src/generation/agents/polish.py
git rm src/generation/polish.py
git commit -m "refactor(generation): move PolishAgent to agents/polish.py"
```

---

## Task 6: 更新 pipeline.py 的 import 和清理 dead code

**Files:**
- Modify: `src/generation/pipeline.py`

- [ ] **Step 1: 分析 pipeline.py 当前 import**

第 6-11 行：
```python
from src.generation.models import ManuscriptResult
from src.generation.outline_agent import OutlineAgent      # ← 需要改
from src.generation.polish import PolishAgent              # ← 需要改
from src.generation.state import WritingPhase, WritingState
from src.generation.style_agent import StyleLearningAgent  # ← 需要改
from src.generation.writer import ChapterWriter             # ← 需要改
```

第 37-40 行（dead code）：
```python
self.outliner = OutlineAgent(debug_mode=debug_mode)        # ← 移除
self.style_learner = StyleLearningAgent(debug_mode=debug_mode)  # ← 移除
```

第 111-124 行（outliner 使用处，需要移除或保留）：
```python
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
```

需要决定这个方法是否保留。如果 `outliner` 已移除，此方法不再有意义。

第 130-146 行（style_learner 使用处）：
```python
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
```

同样，`style_learner` 已移除，此方法不再有意义。

**决策：** 由于 `run()` 方法目前未调用这两个方法，它们是 dead code。移除：
- `_load_or_build_outline` 方法（第 111-124 行）
- `_load_or_build_style_profile` 方法（第 130-146 行）
- `_outline_path` 方法（第 126-128 行）
- `_style_profile_path` 方法（第 148-150 行）
- `_build_outline_fallback` 方法（第 166-181 行）
- `_build_style_profile_fallback` 方法（第 152-164 行）

同时移除这些 dead code 后，pipeline.py 会更简洁。

- [ ] **Step 2: 更新 pipeline.py**

新的 import 部分（第 6-11 行）：
```python
from src.generation.models import ManuscriptResult
from src.generation.agents.outline import OutlineAgent
from src.generation.agents.polish import PolishAgent
from src.generation.state import WritingPhase, WritingState
from src.generation.agents.style import StyleLearningAgent
from src.generation.agents.writer import ChapterWriter
```

新的 `__init__` 部分（第 36-41 行）：
```python
self.outliner = OutlineAgent(debug_mode=debug_mode)
self.style_learner = StyleLearningAgent(debug_mode=debug_mode)
self.writer = ChapterWriter(debug_mode=debug_mode)
self.polisher = PolishAgent(debug_mode=debug_mode)
```

移除 `_load_or_build_outline`、`_load_or_build_style_profile`、`_outline_path`、`_style_profile_path`、`_build_outline_fallback`、`_build_style_profile_fallback` 这些方法和它们在 `run()` 中的调用。

**注意：** 当前 `run()` 方法第 58 行使用了未定义的 `total` 变量（bug）。需要先修复此 bug。`total` 应为 `len(chunks)`。

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/pipeline.py`
Expected: 无输出（成功）

- [ ] **Step 4: 提交**

```bash
git add src/generation/pipeline.py
git commit -m "refactor(generation): update pipeline.py imports and remove dead code"
```

---

## Task 7: 更新根目录 __init__.py 导出

**Files:**
- Modify: `src/generation/__init__.py`

- [ ] **Step 1: 读取当前 __init__.py**

内容：
```python
from .models import ChapterDraft, ManuscriptResult
from .state import WritingPhase, WritingState
from .outline_agent import OutlineAgent
from .research_tools import ManuscriptResearchToolkit
from .style_agent import StyleLearningAgent
from .writer import ChapterWriter
from .polish import PolishAgent
from .pipeline import ManuscriptPipeline

__all__ = [
    "ChapterDraft",
    "ManuscriptResult",
    "WritingPhase",
    "WritingState",
    "OutlineAgent",
    "ManuscriptResearchToolkit",
    "StyleLearningAgent",
    "ChapterWriter",
    "PolishAgent",
    "ManuscriptPipeline",
]
```

- [ ] **Step 2: 更新 import 路径**

```python
from .models import ChapterDraft, ManuscriptResult
from .state import WritingPhase, WritingState
from .agents.outline import OutlineAgent
from .research_tools import ManuscriptResearchToolkit
from .agents.style import StyleLearningAgent
from .agents.writer import ChapterWriter
from .agents.polish import PolishAgent
from .pipeline import ManuscriptPipeline

__all__ = [
    "ChapterDraft",
    "ManuscriptResult",
    "WritingPhase",
    "WritingState",
    "OutlineAgent",
    "ManuscriptResearchToolkit",
    "StyleLearningAgent",
    "ChapterWriter",
    "PolishAgent",
    "ManuscriptPipeline",
]
```

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/__init__.py`
Expected: 无输出（成功）

- [ ] **Step 4: 提交**

```bash
git add src/generation/__init__.py
git commit -m "refactor(generation): update __init__.py imports to agents package"
```

---

## Task 8: 验证无 import 错误

**Files:**
- Test: 多个文件的 import

- [ ] **Step 1: 验证 generation 包导入**

Run: `cd /d/project/storySummary && python -c "from src.generation import ManuscriptPipeline, OutlineAgent, StyleLearningAgent, ChapterWriter, PolishAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 2: 验证 pipeline 导入**

Run: `python -c "from src.generation.pipeline import ManuscriptPipeline; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 检查 api/routers/books.py 是否需要更新**

Run: `grep -n "from src.generation" src/api/routers/books.py`
Expected: 应只有 `from src.generation.pipeline import ManuscriptPipeline`，路径已正确

- [ ] **Step 4: 检查是否有其他文件引用了旧路径**

Run: `grep -rn "from src.generation.outline_agent\|from src.generation.style_agent\|from src.generation.writer\|from src.generation.polish" --include="*.py" .`
Expected: 无输出

- [ ] **Step 5: 提交验证**

```bash
git add -A
git commit -m "chore(generation): verify all imports work after refactor"
```

---

## 自检清单

- [ ] 所有 agent 文件已移入 `agents/` 子包
- [ ] `pipeline.py` 已更新 import 路径
- [ ] `pipeline.py` 已移除 dead code（outliner/style_learner 初始化）
- [ ] `writer.py` 中不存在的 `StoryContext.build_memory` 引用已移除
- [ ] `__init__.py` 已更新导出路径
- [ ] `api/routers/books.py` 无需修改（只有一处 `from src.generation.pipeline import`）
- [ ] 无残留旧路径的 import
- [ ] 所有 Python 文件语法正确

---

## 预期最终结构

```
src/generation/
├── __init__.py
├── models.py
├── state.py
├── pipeline.py
├── research_tools.py
└── agents/
    ├── __init__.py
    ├── outline.py
    ├── style.py
    ├── writer.py
    └── polish.py
```