# src/generation 重构设计

## 目标

重组 `src/generation/` 包，建立清晰的模块边界。

## 当前问题

1. `outline_agent.py` 和 `style_agent.py` 存在但未在 `__init__.py` 导出
2. `WritingPhase` 在 `state.py`，`ChapterDraft` 在 `models.py`，边界不一致
3. `writer.py` 引用不存在的 `StoryContext.build_memory`
4. `pipeline.py` 中 `outliner`/`style_learner` 已初始化但 `run()` 中未使用（dead code）
5. 所有 LLM agent 散落在根目录，结构不清晰

## 目标结构

```
src/generation/
├── __init__.py              # 统一导出
├── models.py                 # 数据模型（ChapterDraft, ManuscriptResult）
├── state.py                  # 状态管理（WritingPhase, WritingState）
├── pipeline.py               # 主编排流程
├── agents/
│   ├── __init__.py           # agents 包导出
│   ├── outline.py            # OutlineAgent
│   ├── style.py              # StyleLearningAgent
│   ├── writer.py             # ChapterWriter
│   └── polish.py             # PolishAgent
└── research_tools.py         # ManuscriptResearchToolkit（保留在根目录）
```

## 实施步骤

### 1. 创建 agents/ 目录结构

### 2. 移动文件

| 原路径 | 新路径 |
|--------|--------|
| `src/generation/outline_agent.py` | `src/generation/agents/outline.py` |
| `src/generation/style_agent.py` | `src/generation/agents/style.py` |
| `src/generation/writer.py` | `src/generation/agents/writer.py` |
| `src/generation/polish.py` | `src/generation/agents/polish.py` |

### 3. 更新 import

- `pipeline.py`: 更新所有 `from src.generation.outline_agent import` → `from src.generation.agents.outline import`
- `__init__.py`: 更新导出路径
- `writer.py`: 修复不存在的 `StoryContext.build_memory` 引用

### 4. 清理 dead code

从 `pipeline.py` 中移除 `outliner` 和 `style_learner` 的初始化（未使用）。

### 5. 更新 __all__ 导出

确保 `agents/__init__.py` 正确导出所有 agent。

## 文件变更详情

### research_tools.py

保留在根目录 `src/generation/research_tools.py`，作为 shared tooling。

### writer.py 修复

移除不存在的 `StoryContext.build_memory` 调用。