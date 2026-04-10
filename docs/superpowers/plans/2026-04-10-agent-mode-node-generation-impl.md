# Agent Mode Node Generation — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Langchain bind_tools tool calling to NarrativeNodeGenerator so the LLM can query previous chunk nodes, thread state, and character mappings during node generation.

**Architecture:** Three SQLite-backed tools (T1/T2/T3) are bound to the LLM via `bind_tools`. When the LLM calls a tool, the tool executor looks up data via existing database methods and returns JSON. A tool-call loop handles up to N rounds before final JSON output.

**Tech Stack:** langchain-core `@tool`, langchain_openai `bind_tools`, SQLite (existing storage layer)

---

## File Map

```
src/core/
  ├── node_generator.py           # modified: add book_id, bind_tools, TOOL_REGISTRY, tool loop
  ├── prompts.py                   # modified: remove timeline_order int, add tool usage + timeline rules
  └── tools/
        ├── __init__.py           # new: exports T1, T2, T3
        ├── node_query_tools.py   # new: @tool T1, T2, T3 function signatures
        └── tool_executor.py      # new: TOOL_REGISTRY + SQLite implementations

tests/core/
  └── test_node_query_tools.py    # new: tests for T1, T2, T3
```

---

## Chunk 1: Tool Definitions

**Files:**
- Create: `src/core/tools/__init__.py`
- Create: `src/core/tools/node_query_tools.py`
- Create: `src/core/tools/tool_executor.py`
- Modify: `src/core/node_generator.py` (add book_id to __init__)

- [ ] **Step 1: Create src/core/tools/__init__.py**

```python
"""Node query tools for agent-mode node generation."""

from src.core.tools.node_query_tools import (
    get_previous_chunk_nodes,
    get_thread_last_node,
    search_nodes,
)

__all__ = [
    "get_previous_chunk_nodes",
    "get_thread_last_node",
    "search_nodes",
]
```

- [ ] **Step 2: Create src/core/tools/node_query_tools.py**

```python
"""Tool definitions using langchain_core @tool decorator."""

from langchain_core.tools import tool


@tool
def get_previous_chunk_nodes(book_id: str) -> list[dict]:
    """Get all nodes from the previous chunk.

    Use this to understand the time anchor (timeline_anchor) of the
    chunk that came before the current one.

    "Previous chunk" means the chunk immediately before the current
    one in sequential processing order. Only one chunk's nodes are returned.

    Returns:
        list of dicts with keys:
        - id: node ID
        - timeline_anchor: time anchor string (e.g., "现在", "一年前")
        - thread_id: thread identifier
        - characters: list of character names in this node
        - narrative_role: opening/rising/climax/ending

    Note: scene text is NOT returned (too large). Use search_nodes for scene search.
    """
    raise NotImplementedError("Implemented in tool_executor.py")


@tool
def get_thread_last_node(book_id: str, thread_id: str) -> dict | None:
    """Get the last (newest) node in a given thread's chain.

    Use this to fill in thread_prev_node_id when creating a new node
    in an existing thread. The returned node is the tail of the
    thread_prev_node_id linked list.

    Args:
        book_id: which book to search
        thread_id: e.g. 'main', 'zhang', 'chenwei', 'laozhou'

    Returns:
        dict with keys: id, timeline_anchor, beat_index
        or None if this thread has no previous nodes (i.e., this is the first node in this thread)
    """
    raise NotImplementedError("Implemented in tool_executor.py")


@tool
def search_nodes(book_id: str, keyword: str) -> list[dict]:
    """Search nodes by character name or scene keyword.

    Uses SQLite LIKE matching (not vector search). Keyword matches
    against character names in nodes.

    Use this to find which thread a character belongs to, to correctly
    assign thread_id for a new node.

    Args:
        book_id: which book to search
        keyword: character name to search for

    Returns:
        list of dicts with keys: id, thread_id, scene (truncated to 50 chars), characters
    """
    raise NotImplementedError("Implemented in tool_executor.py")
```

- [ ] **Step 3: Create src/core/tools/tool_executor.py**

```python
"""Tool implementations — SQLite queries via existing storage layer."""

import json
from src.storage.database import Database


def get_previous_chunk_nodes_impl(book_id: str, **kwargs) -> list[dict]:
    """Get all nodes from the previous chunk (T1 implementation).

    Queries the database for the highest-order chunk less than the current one,
    then returns all nodes in that chunk.
    """
    db = Database()
    # Get all chunks for this book, find the one before current
    chunks = db.get_chunks_for_book(book_id)
    if not chunks:
        return []

    # chunks are dicts with 'id' and 'order' fields
    # Find the previous chunk (highest order less than current)
    # Since we don't know "current" chunk here, return the last chunk in the list
    # The caller (node_generator) should pass parent_chunk_id to narrow it down
    # For now: return all nodes from the last chunk
    if not chunks:
        return []

    last_chunk = max(chunks, key=lambda c: c.get("order", 0))
    last_chunk_id = last_chunk.get("id", "")
    if not last_chunk_id:
        return []

    nodes = db.get_nodes_for_book(book_id)
    prev_nodes = [
        {
            "id": n.id,
            "timeline_anchor": n.timeline_anchor,
            "thread_id": n.thread_id,
            "characters": [c.name for c in n.characters],
            "narrative_role": n.narrative_role,
        }
        for n in nodes
        if n.parent_chunk_id == last_chunk_id
    ]
    return prev_nodes


def get_thread_last_node_impl(book_id: str, thread_id: str, **kwargs) -> dict | None:
    """Get the last node in a thread chain (T2 implementation).

    Finds the node in the given thread that has no incoming thread_next_node_id.
    """
    db = Database()
    nodes = db.get_nodes_for_book(book_id)

    thread_nodes = [n for n in nodes if n.thread_id == thread_id]
    if not thread_nodes:
        return None

    # Find tail: node that no other node points to as its thread_next
    tails = set()
    all_next_ids = {n.thread_next_node_id for n in thread_nodes if n.thread_next_node_id}

    for n in thread_nodes:
        if n.id not in all_next_ids:
            tails.add(n.id)

    if not tails:
        return None

    # Return the one with highest beat_index (most recent)
    tail_node = max(thread_nodes, key=lambda n: n.beat_index)
    return {
        "id": tail_node.id,
        "timeline_anchor": tail_node.timeline_anchor,
        "beat_index": tail_node.beat_index,
    }


def search_nodes_impl(book_id: str, keyword: str, **kwargs) -> list[dict]:
    """Search nodes by character name (T3 implementation)."""
    db = Database()
    nodes = db.get_nodes_for_book(book_id)

    results = []
    for n in nodes:
        char_names = [c.name for c in n.characters]
        if any(keyword in name for name in char_names):
            results.append({
                "id": n.id,
                "thread_id": n.thread_id,
                "scene": n.scene[:50] if n.scene else "",
                "characters": char_names,
            })
    return results


# TOOL_REGISTRY maps tool name → implementation function
TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
}
```

- [ ] **Step 4: Modify node_generator.py — add book_id to __init__**

Find the `__init__` method and add `book_id` parameter:

```python
class NarrativeNodeGenerator:
    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id
        self.model_name = model or os.getenv("LLM_MODEL", "deepseek-chat")
        self.llm = create_llm(api_key=api_key, model=self.model_name, temperature=0.7)
        self.output_parser = JsonOutputParser(pydantic_schema=NarrativeBeatsOutput)
```

- [ ] **Step 5: Run import test**

```bash
python -c "from src.core.tools import get_previous_chunk_nodes, get_thread_last_node, search_nodes; print('OK')"
```

- [ ] **Step 6: Commit**

```bash
git add src/core/tools/__init__.py src/core/tools/node_query_tools.py src/core/tools/tool_executor.py src/core/node_generator.py
git commit -m "feat: add tool definitions and executor for agent-mode node generation"
```

---

## Chunk 2: Tool Execution Loop

**Files:**
- Modify: `src/core/node_generator.py`

- [ ] **Step 1: Add imports and TOOL_REGISTRY**

At top of node_generator.py, add:

```python
from src.core.tools.node_query_tools import get_previous_chunk_nodes, get_thread_last_node, search_nodes
from src.core.tools.tool_executor import TOOL_REGISTRY
from langchain_core.messages import ToolMessage
```

- [ ] **Step 2: Modify generate_from_chunk to use bind_tools**

Replace the `ainvoke` call with:

```python
async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
    prompt = MULTI_BEAT_NODE_PROMPT.format(
        text=chunk.text,
        chunk_order=chunk.order
    )
    format_instructions = self.output_parser.get_format_instructions()
    full_prompt = f"{prompt}\n\n{format_instructions}"

    messages = [
        SystemMessage(content="You are a narrative analyst that outputs valid JSON."),
        HumanMessage(content=full_prompt)
    ]

    # Bind tools to LLM
    llm_with_tools = self.llm.bind_tools([get_previous_chunk_nodes, get_thread_last_node, search_nodes])

    response = await llm_with_tools.ainvoke(messages)

    # Tool call loop
    max_calls = 5
    call_count = 0
    while response.tool_calls and call_count < max_calls:
        call_count += 1
        for tc in response.tool_calls:
            impl = TOOL_REGISTRY.get(tc.name)
            if impl:
                try:
                    result = impl(book_id=self.book_id, **tc.args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"unknown tool: {tc.name}"}
            messages.append(ToolMessage(
                name=tc.name,
                content=json.dumps(result, ensure_ascii=False)
            ))
        response = await llm_with_tools.ainvoke(messages)

    parsed = self.output_parser.parse(response.content)
    # ... rest unchanged (beats_list parsing and node construction)
```

- [ ] **Step 3: Add json import if not present**

Check if `import json` exists at top. If not, add it.

- [ ] **Step 4: Run existing tests**

```bash
pytest tests/core/test_node_generator.py -v
```

Expected: 2 tests pass

- [ ] **Step 5: Commit**

```bash
git add src/core/node_generator.py
git commit -m "feat: add bind_tools and tool execution loop to generate_from_chunk"
```

---

## Chunk 3: Update Prompts

**Files:**
- Modify: `src/core/prompts.py`

- [ ] **Step 1: Add tool usage + timeline rules before JSON schema**

In MULTI_BEAT_NODE_PROMPT, find the section that says `## 输出格式` followed by `## 时间与叙事线标注规则`. Replace the existing `## 时间与叙事线标注规则` section content with:

```
## 工具使用规则

在填写时间/叙事线字段时，如果不确定：
- 调用 get_previous_chunk_nodes 了解上一个 chunk 的时间锚点
- 调用 get_thread_last_node 确认某条叙事线的最新节点
- 调用 search_nodes 查找某角色在哪些节点出现过

格式：先思考（reasoning），再调用工具（tool_call）。

## 时间坐标规则（简化版）

timeline_order 是本 chunk 内的相对顺序，不是全局故事时间。
- "现在"（本 chunk 主线）填 0
- 跳到过去：每往"前"一个时间单位，timeline_order 减 1
- 跳到未来：每往"后"一个时间单位，timeline_order 加 1
- 如果没有时间跳跃，所有节点填 0
```

- [ ] **Step 2: Update timeline_order description in JSON schema**

Find `"timeline_order": 0,` in the JSON schema and update its comment:

```json
    "timeline_order": 0,
    // 新: 本chunk内相对顺序: 0=现在, -1=过去一步, +1=未来一步
```

- [ ] **Step 3: Verify prompt loads**

```bash
python -c "from src.core.prompts import MULTI_BEAT_NODE_PROMPT; print('OK', len(MULTI_BEAT_NODE_PROMPT))"
```

- [ ] **Step 4: Commit**

```bash
git add src/core/prompts.py
git commit -m "feat: add tool usage rules and timeline_order semantics to prompt"
```

---

## Chunk 4: Write Tool Tests

**Files:**
- Create: `tests/core/test_node_query_tools.py`

- [ ] **Step 1: Write tests for T1, T2, T3**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.tools.tool_executor import (
    get_previous_chunk_nodes_impl,
    get_thread_last_node_impl,
    search_nodes_impl,
    TOOL_REGISTRY,
)


class TestTOOLREGISTRY:
    def test_all_three_tools_registered(self):
        assert "get_previous_chunk_nodes" in TOOL_REGISTRY
        assert "get_thread_last_node" in TOOL_REGISTRY
        assert "search_nodes" in TOOL_REGISTRY

    def test_get_previous_chunk_returns_list(self):
        # Empty DB case
        result = get_previous_chunk_nodes_impl(book_id="nonexistent")
        assert isinstance(result, list)

    def test_get_thread_last_node_returns_none_for_unknown_thread(self):
        result = get_thread_last_node_impl(book_id="nonexistent", thread_id="unknown")
        assert result is None

    def test_search_nodes_returns_list(self):
        result = search_nodes_impl(book_id="nonexistent", keyword="李岚")
        assert isinstance(result, list)
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/core/test_node_query_tools.py -v
```

Expected: 4 tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/core/test_node_query_tools.py
git commit -m "test: add tool executor unit tests"
```

---

## Chunk 5: Integration Test

**Files:**
- Modify: `tests/core/test_node_generator.py`

- [ ] **Step 1: Verify existing tests still pass with new code**

```bash
pytest tests/core/test_node_generator.py -v
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all pass

- [ ] **Step 3: Commit (no changes needed if tests pass)**

```bash
git commit -m "test: verify backward compatibility with agent-mode changes"
```
