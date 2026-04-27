# OutlineAgent 重构设计

## 目标

重构 `OutlineAgent`，使其输出**结构化 JSON**，包含故事梗概和口播稿大纲两部分。

## 输入

- `chunks`: 原始章节列表
- `nodes`: 叙事节点列表
- `book_id`: 书籍 ID（用于工具检索）
- `reference_script`: 参考口播稿（可选，用于学习口播风格和结构）

## 输出结构

```json
{
  "story_synopsis": "全文故事情节摘要，描述核心剧情脉络、人物关系变化、关键转折点...",
  "manuscript_outline": [
    {
      "section": "开篇介绍",
      "type": "author_intro",
      "description": "介绍书籍背景、作者、创作动机等"
    },
    {
      "section": "第1章",
      "type": "story_content",
      "chapter": 1,
      "description": "本章核心内容概述"
    },
    {
      "section": "第2章",
      "type": "story_content",
      "chapter": 2,
      "description": "本章核心内容概述"
    },
    {
      "section": "思考与总结",
      "type": "reflection",
      "description": "读后感、主题思考、推荐理由等"
    }
  ],
  "metadata": {
    "total_sections": 15,
    "estimated_duration": "约2小时",
    "tone": "口语化、亲切、故事感"
  }
}
```

## Section Type 分类

| type | 说明 |
|------|------|
| `author_intro` | 作者/书籍介绍 |
| `story_content` | 故事情节内容（含 chapter 编号）|
| `reflection` | 思考、总结、感悟 |

## 实施步骤

### 1. 修改 OutlineAgent.build_outline()

**方法签名：**

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

**优化后的阶段1：批量生成章节摘要**

原逻辑：逐章调用 LLM，20 章 = 20 次 API 调用

新逻辑：利用 1M 上下文窗口，**批量处理**章节摘要

- 每批 5-10 章合并一次 LLM 调用
- 20 章 → 2-4 次调用（取决于章节长度）
- 阶段1 改为 `batch_summarize_chapters()`

**批量摘要示例（每批 5 章）：**
```
请为以下 5 章生成摘要，输出 5 个独立章节摘要块：

## 第1章: xxx
[摘要内容]

## 第2章: xxx
[摘要内容]

## 第3章: xxx
[摘要内容]
...
```

**保留逻辑：**
- 使用 LLM agent + tools 做全书统筹

**修改逻辑：**
- 阶段2 利用阶段1的章节摘要，生成结构化 JSON
- 首先根据摘要提炼 `story_synopsis`（故事梗概）
- 然后基于 `story_synopsis` 和口播风格，生成 `manuscript_outline`（口播稿大纲）
- system_prompt 指导 LLM 输出指定 JSON 格式
- 如果提供了 `reference_script`，从中学习口播风格，调整 `metadata.tone`
- manuscript_outline 按 type 分类：author_intro, story_content, reflection

### 2. 返回值类型

返回 JSON 字符串，由调用方解析为 dict 或直接存储。

## 现有代码参考

- `research_tools.py` - 提供 lookup_original_text 和 vector_retrieve 工具
- 阶段1 逐章摘要逻辑保持不变
- 阶段2 改为生成结构化 JSON