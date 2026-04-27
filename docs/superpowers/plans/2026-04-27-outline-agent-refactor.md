# OutlineAgent 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 OutlineAgent，输出结构化 JSON（故事梗概 + 口播稿大纲），批量生成章节摘要提升效率。

**Architecture:** 保持两阶段架构（摘要生成 → 结构化输出），阶段1 改为批量处理，阶段2 输出 JSON。

**Tech Stack:** Python, LLM API, JSON

---

## 任务总览

| Task | 描述 |
|------|------|
| 1 | 修改 build_outline() 方法签名，添加 reference_script 参数 |
| 2 | 实现 batch_summarize_chapters() 批量摘要方法 |
| 3 | 修改阶段2 system_prompt，输出结构化 JSON |
| 4 | 实现 generate_manuscript_outline() 生成口播稿大纲 |
| 5 | 验证输出 JSON 格式正确 |

---

## Task 1: 修改 build_outline() 方法签名

**Files:**
- Modify: `src/generation/agents/outline.py:23-30`

- [ ] **Step 1: 添加 reference_script 参数到方法签名**

修改 `build_outline()` 方法签名，添加可选参数 `reference_script: str | None = None`

原始代码：
```python
async def build_outline(
    self,
    book_id: str,
    chunks: list[Chunk],
    nodes: list[NarrativeNode],
    progress_callback: Callable[[str], None] | None = None,
) -> str:
```

新代码：
```python
async def build_outline(
    self,
    book_id: str,
    chunks: list[Chunk],
    nodes: list[NarrativeNode],
    progress_callback: Callable[[str], None] | None = None,
    reference_script: str | None = None,
) -> str:  # 返回 JSON 字符串
```

- [ ] **Step 2: 在 emit 消息中报告 reference_script 状态**

在方法内部，在报告阶段时说明是否使用了参考口播稿。

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile src/generation/agents/outline.py`
Expected: 无输出（成功）

- [ ] **Step 4: 提交**

```bash
git add src/generation/agents/outline.py
git commit -m "feat(outline): add reference_script parameter to build_outline"
```

---

## Task 2: 实现 batch_summarize_chapters() 批量摘要方法

**Files:**
- Modify: `src/generation/agents/outline.py`
- Replace: `_build_chapter_summaries()` 逻辑

- [ ] **Step 1: 分析现有 _build_chapter_summaries() 逻辑**

现有方法逐章调用 LLM，共 20 次 API 调用。需要改为批量处理。

- [ ] **Step 2: 创建 batch_summarize_chapters() 方法**

新方法签名：
```python
async def batch_summarize_chapters(
    self,
    chunks: list[Chunk],
    nodes_by_chunk: dict[str, list[NarrativeNode]],
    progress_callback: Callable[[str], None] | None = None,
) -> str:
```

逻辑：
1. 按 5 章一批分组
2. 每批构建一个 prompt，包含 5 章的 node_text 和 chunk_preview
3. 调用一次 LLM 获取 5 章的摘要
4. 合并所有批次的摘要

**批量摘要 system_prompt：**
```
你是章节摘要助手。只总结当前章节，不跨章推理。
- 忠于原文，不补写剧情。
- 输出紧凑，突出事件推进、关系变化、伏笔信号和章节亮点。
- 每个章节输出格式：## 第X章: xxx\n[摘要内容]
```

**批量摘要 user_prompt 格式：**
```
请为以下 {n} 章生成摘要，输出 {n} 个独立章节摘要块：

## 第1章: {chapter_name}
节点线索：
{node_text_1}
原文预览：
{chunk_preview_1}

## 第2章: {chapter_name}
节点线索：
{node_text_2}
原文预览：
{chunk_preview_2}

... (以此类推到第N章)
```

- [ ] **Step 3: 更新 build_outline() 调用新方法**

将 `chapter_summaries = await self._build_chapter_summaries(...)` 改为调用 `batch_summarize_chapters()`

- [ ] **Step 4: 删除旧的 _build_chapter_summaries() 方法**

- [ ] **Step 5: 验证语法**

Run: `python -m py_compile src/generation/agents/outline.py`
Expected: 无输出（成功）

- [ ] **Step 6: 提交**

```bash
git add src/generation/agents/outline.py
git commit -m "feat(outline): implement batch chapter summarization"
```

---

## Task 3: 修改阶段2 system_prompt，输出结构化 JSON

**Files:**
- Modify: `src/generation/agents/outline.py:build_outline() 阶段2 部分`

- [ ] **Step 1: 分析现有阶段2代码**

现有阶段2使用 agent 生成纯文本 outline。需要改为生成 JSON。

- [ ] **Step 2: 编写新的 system_prompt**

新 system_prompt：
```
你是资深故事编辑，负责生成结构化口播稿大纲。

## 你的任务
1. 根据章节摘要提炼全书故事梗概（story_synopsis）
2. 规划口播稿结构（manuscript_outline）

## 输出格式
必须输出有效的 JSON 字符串，格式如下：
{
  "story_synopsis": "全文故事情节摘要，包含核心人物、核心冲突、关键转折、结局",
  "manuscript_outline": [
    {"section": "开篇介绍", "type": "author_intro", "description": "..."},
    {"section": "第X章", "type": "story_content", "chapter": X, "description": "..."},
    {"section": "思考与总结", "type": "reflection", "description": "..."}
  ],
  "metadata": {
    "total_sections": 15,
    "estimated_duration": "约2小时",
    "tone": "口语化、亲切、故事感"
  }
}

## Section Type 分类
- author_intro: 作者/书籍介绍
- story_content: 故事情节内容（必须包含 chapter 编号）
- reflection: 思考、总结、感悟

## 要求
- 必须忠于原始章节与叙事节点，不补写不存在的剧情
- manuscript_outline 必须覆盖所有章节
- 如果有参考口播稿，学习其风格并调整 metadata.tone
```

- [ ] **Step 3: 更新阶段2的 user_prompt**

user_prompt 应包含章节摘要，并说明需要生成 JSON：
```
你将拿到逐章摘要初稿。请先审查并纠偏，再输出结构化 JSON 大纲。

逐章摘要初稿如下：
{chapter_summaries}

请直接输出 JSON，不要包含任何其他内容。"""

- [ ] **Step 4: 验证 JSON 输出可以解析**

在 `_extract_output()` 之后，添加 JSON 解析验证：
```python
output = self._extract_output(response)
if not output:
    raise ValueError("OutlineAgent returned empty response")

# 尝试解析为 JSON
try:
    import json
    result = json.loads(output)
except json.JSONDecodeError:
    raise ValueError("OutlineAgent did not return valid JSON")
```

- [ ] **Step 5: 验证语法**

Run: `python -m py_compile src/generation/agents/outline.py`
Expected: 无输出（成功）

- [ ] **Step 6: 提交**

```bash
git add src/generation/agents/outline.py
git commit -m "feat(outline): output structured JSON for manuscript outline"
```

---

## Task 4: 实现 generate_manuscript_outline() 生成口播稿大纲

**Files:**
- Modify: `src/generation/agents/outline.py`
- Add: 新方法 `generate_manuscript_outline()`

**注意：** 根据设计，阶段2流程是：
1. 先生成 story_synopsis（从章节摘要提炼）
2. 再基于 story_synopsis 生成 manuscript_outline

由于使用了 JSON prompt，LLM 可以同时生成两者。但如果需要分步生成，可以创建独立方法。

- [ ] **Step 1: 分析是否需要分步生成**

当前设计中，system_prompt 要求 LLM 同时输出 story_synopsis 和 manuscript_outline。如果输出不稳定，可以考虑分步调用。

- [ ] **Step 2: 如需要，创建 generate_manuscript_outline() 方法**

如果分步实现：
```python
async def generate_manuscript_outline(
    self,
    story_synopsis: str,
    chapters: list[Chunk],
    reference_script: str | None = None,
) -> list[dict]:
    """基于故事梗概生成口播稿大纲"""
    # ...
```

- [ ] **Step 3: 如果当前单步可以满足，跳过此任务**

如果 JSON prompt 可以稳定输出 story_synopsis + manuscript_outline，此任务可以跳过。

- [ ] **Step 4: 提交（如果执行了）**

```bash
git add src/generation/agents/outline.py
git commit -m "feat(outline): add generate_manuscript_outline method"
```

---

## Task 5: 验证输出 JSON 格式正确

**Files:**
- Test: `src/generation/agents/outline.py`

- [ ] **Step 1: 验证 JSON 输出结构**

检查输出的 JSON 包含：
1. `story_synopsis`: str 类型
2. `manuscript_outline`: list 类型
3. `metadata`: dict 类型
4. 每个 outline 元素包含 `section`, `type`, `description`
5. `story_content` 类型包含 `chapter` 字段

- [ ] **Step 2: 运行单元测试（如果存在）**

Run: `python -m pytest tests/ -v -k outline` 或类似命令

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "test(outline): verify JSON output structure"
```

---

## 自检清单

- [ ] build_outline() 方法签名包含 reference_script 参数
- [ ] 批量摘要每批 5 章，减少 API 调用次数
- [ ] 阶段2 输出有效 JSON 字符串
- [ ] JSON 可解析，包含 story_synopsis + manuscript_outline + metadata
- [ ] manuscript_outline 按 type 分类（author_intro, story_content, reflection）
- [ ] story_content 类型包含 chapter 字段

---

## 预期最终方法签名

```python
async def build_outline(
    self,
    book_id: str,
    chunks: list[Chunk],
    nodes: list[NarrativeNode],
    progress_callback: Callable[[str], None] | None = None,
    reference_script: str | None = None,
) -> str:  # 返回 JSON 字符串
```