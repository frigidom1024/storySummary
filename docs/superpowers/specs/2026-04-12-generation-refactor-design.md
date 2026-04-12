# Generation 包重构设计

## 目标

重构 `src/generation/` 包，提供统一、简洁的对外接口，清晰的状态管理，以及规范的生成流程。

## 整体流程

```
run(book_id)
  │
  ├─> 1. [PREPARE] 加载所有 nodes → 喂给 AI 建立全局理解
  │
  ├─> 2. [WRITING] 遍历 chunk（按需加载）
  │       ├─> 加载当前 chunk 原文 + 对应 nodes
  │       ├─> context.build_prompt_context()
  │       ├─> ChapterWriter.write()
  │       ├─> context.update_draft()
  │       └─> state.save()
  │
  └─> 3. [POLISHING] 润色 draft → 保存
```

## 目录结构

```
src/generation/
  __init__.py       # 导出 ManuscriptPipeline
  pipeline.py       # 主入口 ManuscriptPipeline
  state.py          # WritingState 断点状态
  context.py        # WritingContext 对话上下文
  writer.py         # ChapterWriter 单章生成
  polish.py         # PolishPass 润色逻辑
  models.py         # 数据模型
```

## 文件职责

### models.py - 数据模型

```python
class ManuscriptResult(BaseModel):
    title: str
    draft: str
    phase: str
    chapters_written: int
    total_chunks: int
```

### state.py - 断点状态

```python
class WritingPhase(str, Enum):
    PREPARE = "prepare"
    WRITING = "writing"
    POLISHING = "polishing"
    DONE = "done"

class WritingState(BaseModel):
    book_id: str
    book_title: str
    phase: WritingPhase
    current_chunk_index: int
    draft: str = ""
    outline: Optional[dict] = None

    def save(path: Path)
    @classmethod def load(cls, path: Path) -> "WritingState"
    @classmethod def get_state_path(cls, book_id: str, output_dir: str) -> Path
```

- 状态文件路径：`output/{book_title}/writing_state.json`
- 草稿完整内容存在 `draft` 字段中，AI 可随时修改

### context.py - 对话上下文

```python
class WritingContext:
    draft: str                          # 当前完整草稿
    context_summary: str                # 草稿摘要（注入提示词用）
    established_facts: list[str]       # 已建立的事实

    def build_prompt_context(self, chunk, nodes) -> str
        # 组合：context_summary + 当前 chunk 信息 + nodes
        # 作为 AI 提示词的一部分

    def update_draft(self, new_draft: str)
        # AI 修改后的完整草稿（可能包含对旧章节的修改）
        # 自动更新 context_summary

    def append_chapter(self, chapter_text: str)
        # 追加新章节到 draft
```

### writer.py - 单章生成

```python
class ChapterWriter:
    def __init__(self, api_key: str, model: str)
    async def write(
        self,
        chunk: Chunk,
        nodes: list[NarrativeNode],
        context_summary: str,
        draft_so_far: str,
    ) -> str:
        # 返回生成的章节文本
        # AI 可以选择续写新章节，或修改 draft_so_far 中的旧内容
```

### polish.py - 润色

```python
class PolishPass:
    def __init__(self, api_key: str, model: str)
    async def polish(self, draft: str) -> str:
        # 返回润色后的完整口播稿
```

### pipeline.py - 主入口

```python
class ManuscriptPipeline:
    def __init__(self, output_dir: str = "output")
    async def run(self, book_id: str) -> ManuscriptResult:
        # 1. 加载 WritingState（支持断点恢复）
        # 2. [PREPARE] 加载所有 nodes，喂给 AI 建立全局理解
        # 3. [WRITING] 遍历 chunk，按需加载原文
        # 4. [POLISHING] 润色
        # 5. 保存最终稿到 output/{book_title}/manuscript.txt
```

## 数据流

```
book_id
  │
  ├─> 加载 WritingState（若存在）
  │
  ├─> [PREPARE]
  │     └─> 加载所有 nodes → context
  │
  ├─> [WRITING] for chunk in chunks[state.current_chunk_index:]:
  │     ├─> 加载 chunk 原文 + 对应 nodes（按需）
  │     ├─> context.build_prompt_context()
  │     ├─> ChapterWriter.write()
  │     ├─> context.update_draft()  # AI 可能修改了之前的内容
  │     ├─> state.draft = context.draft
  │     ├─> state.current_chunk_index += 1
  │     └─> state.save()
  │
  └─> [POLISHING]
          └─> PolishPass.polish() → 保存 manuscript.txt
```

## 错误处理

- API 调用失败：保存当前状态，抛出异常，供调用方重试
- 中断恢复：再次调用 `run()` 时从 `WritingState` 恢复 draft + chunk_index，继续生成

## 依赖

- Python 3.11+
- langchain-openai
- pydantic
- 从 `src.storage.file_manager` 加载书籍数据
