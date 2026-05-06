# 口播稿生成流程重构计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构生成流程为清晰的4阶段：获取梗概与结构 → 获取风格参考 → 迭代写草稿 → 总体润色。每阶段独立存储结果，支持断点续跑。

**Architecture:**
- 新增 `PipelinePhase` 枚举替代 `WritingPhase`，覆盖5个阶段：OUTLINING / STYLE_LEARNING / WRITING / POLISHING / DONE
- `WritingState` 保留最小状态（book_id, phase, current_index），草稿存储完全委托给 `manuscript_repository`
- Pipeline 按阶段顺序执行，每阶段完成后立即存储结果
- 支持断点续跑：检测已完成的阶段并跳过

**Tech Stack:** Python asyncio, Pydantic, manuscript_repository, WritingState

---

## 文件变更概览

| 文件 | 变更 |
|------|------|
| `src/generation/state.py` | 新增 `PipelinePhase` 枚举，修改 `WritingState.phase` 类型 |
| `src/generation/pipeline.py` | 重构为4阶段流程，每阶段独立存储结果 |
| `src/generation/__init__.py` | 导出新增的 `PipelinePhase` |

---

## Task 1: 更新 state.py - 新增 PipelinePhase 枚举

**Files:**
- Modify: `src/generation/state.py:11-14`

- [ ] **Step 1: 添加 PipelinePhase 枚举**

在 `WritingPhase` 之后添加：

```python
class PipelinePhase(str, Enum):
    OUTLINING = "outlining"       # 阶段1：生成梗概和结构
    STYLE_LEARNING = "style_learning"  # 阶段2：学习风格
    WRITING = "writing"           # 阶段3：写草稿
    POLISHING = "polishing"       # 阶段4：润色
    DONE = "done"                 # 完成
```

- [ ] **Step 2: 验证语法正确**

```bash
python -m py_compile src/generation/state.py && echo "OK"
```

---

## Task 2: 更新 pipeline.py - 重构为4阶段流程

**Files:**
- Modify: `src/generation/pipeline.py:1-155`
- Modify: `src/generation/agents/outline.py:119-192`

- [ ] **Step 1: 修改 outline.py - 在 outline 中存储 chunk_id**

在 `build_manuscript_outline` 方法中，构建 outline 时传入 chunks 以关联 chunk_id：

修改 `build_manuscript_outline` 的调用处，传入 story_chunks（包含 id 字段）：

```python
manuscript_outline = await self.build_manuscript_outline(
    chapter_summaries, story_chunks, reference_script, progress_callback=progress_callback
)
```

然后在 `build_manuscript_outline` 方法中，构建 JSON 时加入 `chunk_id`（直接使用 chunk.id）：

```python
# chunk.id 就是 book_repository 存储的 ID，如 "ch_0", "ch_1" 等
for chunk in chunks:
    manuscript_outline.append({
        "section": chunk.chapter or f"第{chunk.order + 1}章",
        "type": "story_content",
        "chapter": chunk.order + 1,
        "chunk_id": chunk.id,  # 直接使用 chunk.id
        "description": ""  # 可选描述
    })
```

- [ ] **Step 2: 更新 outline.py 的签名**

`build_manuscript_outline` 方法签名添加 `chunks: list[Chunk]` 参数：

```python
async def build_manuscript_outline(
    self,
    chapter_summaries: str,
    chunks: list[Chunk],  # 新增，传入 story_chunks
    reference_script: str | None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[dict]:
```

- [ ] **Step 3: 添加阶段检查辅助方法**

在 `ManuscriptPipeline` 类中添加：

```python
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
```

- [ ] **Step 2: 重构 run 方法为阶段化流程**

将 `run` 方法重构为：

```python
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
        await self._run_polish_phase(book_id, state, state_path)
        state.phase = PipelinePhase.DONE
        state.save(state_path)

    await self._report_progress(100, "生成完成")

    return ManuscriptResult(
        title=book.title,
        book_id=book_id,
        drafts=list(manuscript_repository.load_all_drafts(book_id).values()),
        phase=state.phase.value,
    )
```

- [ ] **Step 3: 添加阶段执行方法**

添加以下私有方法：

```python
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
    outline_data = json.loads(manuscript_outline_json)
    manuscript_repository.save_outline(book_id, outline_data)
    
    # 存储章节摘要（如果 outliner 生成了）
    # manuscript_repository.save_chapter_summaries(book_id, chapter_summaries)
    
    await self._report_progress(20, "梗概和结构生成完成")

async def _run_style_phase(self, book_id: str, book_title: str, state, state_path):
    """阶段2：学习风格参考"""
    await self._report_progress(25, "正在学习风格参考...")
    
    if self.reference_script:
        style_profile = await self.style_learner.learn_profile(self.reference_script)
        manuscript_repository.save_style_profile(book_id, style_profile.model_dump())
        return style_profile
    return None

async def _run_writing_phase(self, book_id: str, chunks, nodes, state, state_path, total):
    """阶段3：迭代写草稿 - 遍历 outline 结构，根据类型调用不同 AI"""
    outline_data = manuscript_repository.load_outline(book_id)
    outline_list = outline_data.get("manuscript_outline", []) if outline_data else []
    style_profile = None
    if manuscript_repository.has_style_profile(book_id):
        profile_dict = manuscript_repository.load_style_profile(book_id)
        style_profile = StyleProfile(**profile_dict)

    # 构建 chunks 映射，方便按类型和章节号查找
    chunks_by_type = {}
    for chunk in chunks:
        chunks_by_type.setdefault(chunk.content_type, []).append(chunk)
    nodes_by_chunk = {n.parent_chunk_id: [n for n in nodes if n.parent_chunk_id == chunk_id] for chunk_id in [c.id for c in chunks]}

    total_sections = len(outline_list)
    for i, section in enumerate(outline_list):
        section_id = section.get("section", f"section-{i}")
        section_type = section.get("type")
        chapter_num = section.get("chapter")  # story_content 类型有 chapter 编号

        # 跳过已完成的草稿
        if manuscript_repository.load_draft(book_id, section_id):
            continue

        await self._report_progress(25 + int((i / total_sections) * 55), f"正在生成 {section_id}...")

        if section_type == "author_intro":
            # 开篇介绍 → GuideAgent
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
            # 故事情节 → ChapterWriter
            chunk_id = section.get("chunk_id")
            chunk = next((c for c in chunks if c.id == chunk_id), None)
            if chunk:
                chunk_nodes = nodes_by_chunk.get(chunk.id, [])
                completed_drafts = [Draft(**d) for d in manuscript_repository.load_all_drafts(book_id).values()]
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
            # 总结思考 → GuideAgent
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
    """阶段4：润色"""
    await self._report_progress(85, "正在润色全文...")
    
    all_drafts = manuscript_repository.load_all_drafts(book_id)
    sorted_sections = sorted(all_drafts.keys())
    full_text = "\n\n---\n\n".join(all_drafts[k]["content"] for k in sorted_sections)
    
    chunks = book_repository.load_chunks(book_id)
    polished = await self.polisher.polish(full_text, chunks)
    
    manuscript_repository.save_final_manuscript(book_id, polished)
    await self._report_progress(95, "润色完成")
```

- [ ] **Step 4: 添加 import json**

在 `pipeline.py` 顶部添加：

```python
import json
```

- [ ] **Step 5: 更新 imports**

更新 `from src.generation.state import WritingPhase, WritingState` 为：

```python
from src.generation.state import PipelinePhase, WritingState
```

并添加：

```python
from src.generation.agents.models import Draft
```

- [ ] **Step 6: 删除 _load_or_build_style_profile 方法**

如果存在，删除该方法，因为风格学习已整合到阶段2。

- [ ] **Step 7: 验证语法正确**

```bash
python -m py_compile src/generation/pipeline.py && echo "OK"
```

---

## Task 3: 更新 __init__.py - 导出 PipelinePhase

**Files:**
- Modify: `src/generation/__init__.py:19`

- [ ] **Step 1: 更新导出**

将：

```python
from .state import WritingPhase, WritingState
```

改为：

```python
from .state import PipelinePhase, WritingPhase, WritingState
```

- [ ] **Step 2: 更新 __all__ 列表**

添加 `PipelinePhase` 到导出列表。

- [ ] **Step 3: 验证导出正确**

```bash
python -c "from src.generation import PipelinePhase, WritingState; print('OK')"
```

---

## Task 4: 验证整体流程

**Files:**
- Test: `test_manuscript_pipeline.py`

- [ ] **Step 1: 运行导入测试**

```bash
python -c "from src.generation.pipeline import ManuscriptPipeline; from src.generation.state import PipelinePhase; print('OK')"
```

- [ ] **Step 2: 验证 pipeline 可实例化**

```bash
python -c "
from src.generation.pipeline import ManuscriptPipeline
p = ManuscriptPipeline()
print(f'Pipeline created, phases: {[p.phase.value if hasattr(p, \"phase\") else \"N/A\"]}')"
```

---

## 验证清单

1. `PipelinePhase` 枚举包含5个阶段
2. Pipeline 按顺序执行4个阶段
3. 每阶段完成后立即存储结果到 `manuscript_repository`
4. 支持断点续跑（检测已完成阶段并跳过）
5. `WritingState.phase` 使用 `PipelinePhase` 类型
6. 所有导入正确，无循环依赖
