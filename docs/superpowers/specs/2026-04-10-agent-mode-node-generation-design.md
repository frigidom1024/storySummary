# Narrative Node Generation — Agent Mode Design

Date: 2026-04-10
Status: Draft

## Background

The current `NarrativeNodeGenerator.generate_from_chunk()` is stateless — each chunk is processed independently with no awareness of previous chunks' timeline anchors, thread states, or character mappings. This causes three classes of errors:

1. **Flashback n-0-0 wrong timeline_order**: The LLM assigned `timeline_order=-20` to the opening scene (which is "now/present") because it had no awareness of what "now" is.
2. **Reverse n-0-4/5 same timeline_order**: Two distinct scenes in "four years later" received identical `timeline_order` values because the LLM couldn't track sequence.
3. **Multithread convergence missing thread_prev**: The convergence node had no `thread_prev_node_id` because the LLM couldn't query which nodes were the tails of each thread.

## Design Decision

**Approach: Agent Mode with Langchain bind_tools + SQLite tools (方案 B-1 + B)**

LLM calls tools to query previous nodes during generation, rather than receiving pre-injected context. This keeps `generate_from_chunk` stateless at the call level while providing rich cross-chunk awareness.

**Why not ReAct agent loops**: Tool calls are limited (at most ~5 per generation), so a full ReAct loop is overkill. Using `bind_tools` with manual tool execution is simpler and sufficient.

**Why not context injection**: Pre-injecting all previous nodes bloats the prompt and relies on LLM's context utilization. Tool queries let the LLM fetch exactly what it needs.

## Architecture

```
Pipeline / Caller
  │
  ├── NarrativeNodeGenerator(book_id)       ← book_id injected externally
  │     │
  │     ├── bind_tools([T1, T2, T3])        ← Langchain bind_tools
  │     │
  │     └── generate_from_chunk(chunk)
  │           │
  │           ├── First LLM call → possibly returns tool_calls
  │           │
  │           ├── Loop: execute tools (SQLite) → append ToolMessage
  │           │
  │           └── Second LLM call → final JSON output
  │
  └── Storage (SQLite via existing methods)
        ├── get_nodes_for_book(book_id)
        └── get_structure_for_book(book_id)
```

## Tool Definitions

### T1: get_previous_chunk_nodes

```python
@tool
def get_previous_chunk_nodes(book_id: str) -> list[dict]:
    """Get all nodes from the previous chunk.

    Use this to understand the time anchor (timeline_anchor) of the
    chunk that came before the current one.

    Returns:
        list of dicts with keys: id, timeline_anchor, thread_id,
        characters (list of names), scene, narrative_role
    """
```

### T2: get_thread_last_node

```python
@tool
def get_thread_last_node(book_id: str, thread_id: str) -> dict | None:
    """Get the last (newest) node in a given thread.

    Use this to fill in thread_prev_node_id when creating a new node
    in an existing thread.

    Args:
        book_id: which book to search
        thread_id: e.g. 'main', 'zhang', 'chenwei', 'laozhou'

    Returns:
        dict with keys: id, timeline_anchor, beat_index
        or None if this thread has no previous nodes
    """
```

### T3: search_nodes

```python
@tool
def search_nodes(book_id: str, keyword: str) -> list[dict]:
    """Search nodes by character name or scene keyword.

    Uses SQLite LIKE matching (not vector search).
    Use this to find which thread a character belongs to.

    Args:
        book_id: which book to search
        keyword: character name or scene keyword

    Returns:
        list of dicts with keys: id, thread_id, scene, characters
    """
```

## Timeline Field Adjustment

**Remove**: `timeline_order` (integer, difficult for LLM to estimate, especially in single-chunk context)

**Keep**:
- `timeline_anchor: str` — e.g. "现在", "大学时期", "二十年前", "四年后"
- `is_time_jump: bool`
- `jump_direction: str` — "past" / "future" / ""
- `jump_label: str` — "倒叙" / "插叙" / "回到现在" / ""

Timeline ordering is computed later by `StoryGraph.get_timeline_order()` using anchor semantics (not integer arithmetic).

## Prompt Changes

### MULTI_BEAT_NODE_PROMPT additions

Add a tool-usage section before the JSON schema:

```
## 工具使用规则

在填写时间/叙事线字段时，如果不确定：
- 调用 get_previous_chunk_nodes 了解上一个 chunk 的时间锚点
- 调用 get_thread_last_node 确认某条叙事线的最新节点
- 调用 search_nodes 查找某角色在哪些节点出现过

格式：先思考（reasoning），再调用工具（tool_call）。
```

### JSON schema field removal

Remove `"timeline_order": 0` from the JSON schema in the prompt.

## Tool Execution Loop

```python
async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
    llm_with_tools = self.llm.bind_tools([T1, T2, T3])

    messages = [SystemMessage(content="..."), HumanMessage(content=prompt)]

    response = await llm_with_tools.ainvoke(messages)

    # Tool call loop
    while response.tool_calls:
        for tc in response.tool_calls:
            result = execute_tool(tc.name, tc.args, self.book_id)
            messages.append(ToolMessage(
                name=tc.name,
                content=json.dumps(result)
            ))
        response = await llm_with_tools.ainvoke(messages)

    return self._parse_beats(response.content)
```

## book_id Injection

```python
class NarrativeNodeGenerator:
    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id  # injected externally
        ...
```

The `book_id` flows from pipeline level → generator → tool implementations.

## New File Structure

```
src/core/
  ├── node_generator.py          # modified: add bind_tools, tool loop
  ├── prompts.py                 # modified: remove timeline_order, add tool usage rules
  └── tools/
        ├── __init__.py
        ├── node_query_tools.py   # new: T1, T2, T3 tool definitions
        └── tool_executor.py      # new: execute tool by name, query SQLite
```

## Open Questions / Future Extensions

1. **Convergence node thread_prev**: Currently a single `thread_prev_node_id` cannot represent multiple incoming thread links. Future work: add `thread_prev_node_ids: list[str]` to NarrativeNode.
2. **Vector search T4**: If "find scenes by emotional similarity" is needed for podcast material, add a fourth tool using the existing vector store.
3. **Tool call budget**: Limit max tool calls per generation (e.g., 5) to prevent infinite loops.
