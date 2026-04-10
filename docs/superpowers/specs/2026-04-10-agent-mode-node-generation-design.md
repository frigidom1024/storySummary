# Narrative Node Generation — Agent Mode Design

Date: 2026-04-10
Status: Draft

## Background

The current `NarrativeNodeGenerator.generate_from_chunk()` is stateless — each chunk is processed independently with no awareness of previous chunks' timeline anchors, thread states, or character mappings. This causes three classes of errors:

1. **Flashback n-0-0 wrong timeline_order**: The LLM assigned `timeline_order=-20` to the opening scene (which is "now/present") because it had no awareness of what "now" is.
2. **Reverse n-0-4/5 same timeline_order**: Two distinct scenes in "four years later" received identical `timeline_order` values because the LLM couldn't track sequence.
3. **Multithread convergence missing thread_prev**: The convergence node had no `thread_prev_node_id` because the LLM couldn't query which nodes were the tails of each thread.

## Design Decision

**Approach: Agent Mode with Langchain bind_tools + SQLite tools**

LLM calls tools to query previous nodes during generation, rather than receiving pre-injected context. This keeps `generate_from_chunk` stateless at the call level while providing rich cross-chunk awareness.

**Why not ReAct agent loops**: Tool calls are limited (~5 per generation), so a full ReAct loop is overkill. Using `bind_tools` with manual tool execution is simpler and sufficient.

**Why not context injection**: Pre-injecting all previous nodes bloats the prompt. Tool queries let the LLM fetch exactly what it needs.

## Architecture

```
Pipeline / Caller
  │
  ├── NarrativeNodeGenerator(book_id)       ← book_id injected externally
  │     │
  │     ├── bind_tools([T1, T2, T3])       ← Langchain bind_tools
  │     │
  │     └── generate_from_chunk(chunk)
  │           │
  │           ├── First LLM call → may return tool_calls
  │           │
  │           ├── If tool_calls: execute tools → append ToolMessage
  │           │
  │           └── Second LLM call → final JSON output
  │
  └── Storage (SQLite via existing methods)
        ├── get_nodes_for_book(book_id)
        └── get_structure_for_book(book_id)
```

## Tool Definitions

All tools are defined using `@tool` decorator from `langchain_core.tools`.

### T1: get_previous_chunk_nodes

```python
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
```

### T2: get_thread_last_node

```python
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
```

Returns: `{id, timeline_anchor, beat_index}`

### T3: search_nodes

```python
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
```

Returns: `[{id, thread_id, scene (≤50 chars), characters}, ...]`

## Timeline Field Adjustment

**Change**: `timeline_order` is now a **relative sequence integer** — not an absolute story-chronological position, but a sequential counter relative to the current chunk's internal timeline.

- Chunk 内的 timeline_order 从 0 开始，每往"后"发展一个时间单位 +1，每往"前"（倒叙/插叙）-1
- Example: Chunk 中 scene A 在"现在" → `timeline_order=0`；scene B 跳到"一年前" → `timeline_order=-1`；scene C 再跳到"两年半前" → `timeline_order=-2`；scene D 跳到"四年后" → `timeline_order=+1`
- `timeline_order` 只在**同一个 chunk 内**有相对意义；跨 chunk 的绝对顺序由 `timeline_anchor` 字符串判断
- 如果当前 chunk 没有时间跳跃（单一线性叙事），所有 `timeline_order=0`

**保留字段**：
- `timeline_anchor: str` — 锚点文字："现在"、"大学时期"、"二十年前"、"四年后"
- `is_time_jump: bool`
- `jump_direction: str` — "past" / "future" / ""
- `jump_label: str` — "倒叙" / "插叙" / "回到现在" / ""

**删除字段**：无（`timeline_order` 保留但语义改为"chunk 内相对顺序"）

## Prompt Changes

### MULTI_BEAT_NODE_PROMPT additions

Add before the JSON schema:

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

### JSON schema field change

Update `timeline_order` description:
```json
"timeline_order": 0,
// 新增描述: "本chunk内相对顺序: 0=现在, -1=过去一步, +1=未来一步"
```

## Tool Execution Loop

```python
# src/core/node_generator.py

TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
}


async def generate_from_chunk(self, chunk: Chunk) -> list[NarrativeNode]:
    llm_with_tools = self.llm.bind_tools([T1, T2, T3])

    messages = [
        SystemMessage(content="You are a narrative analyst..."),
        HumanMessage(content=full_prompt)
    ]

    response = await llm_with_tools.ainvoke(messages)

    # Tool call loop: handle all tool calls from LLM
    while response.tool_calls:
        for tc in response.tool_calls:
            # book_id is injected by the executor — NOT from tc.args
            # tc.args contains only the tool-specific args (e.g., thread_id, keyword)
            impl = TOOL_REGISTRY.get(tc.name)
            if impl:
                result = impl(book_id=self.book_id, **tc.args)
            else:
                result = {"error": f"unknown tool: {tc.name}"}
            messages.append(ToolMessage(
                name=tc.name,
                content=json.dumps(result)
            ))
        response = await llm_with_tools.ainvoke(messages)

    return self._parse_beats(response.content)
```

Key point: `book_id` is injected by `TOOL_REGISTRY[tool_name](book_id=..., **tc.args)` — it does NOT come from `tc.args` (which is controlled by the LLM). This prevents a malicious LLM from injecting a different book_id.

## book_id Injection

```python
class NarrativeNodeGenerator:
    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        self.book_id = book_id  # injected externally by pipeline
```

## New File Structure

```
src/core/
  ├── node_generator.py           # modified: bind_tools, tool loop, TOOL_REGISTRY
  ├── prompts.py                  # modified: tool usage rules, updated timeline_order description
  └── tools/
        ├── __init__.py           # new: exports T1, T2, T3
        ├── node_query_tools.py   # new: @tool-decorated T1, T2, T3 function signatures
        └── tool_executor.py      # new: TOOL_REGISTRY + SQLite query implementations
```

**tool_executor.py 内容**：

```python
# TOOL_REGISTRY maps tool name string → implementation function
# Each implementation receives book_id as a keyword arg plus tool-specific args

TOOL_REGISTRY = {
    "get_previous_chunk_nodes": get_previous_chunk_nodes_impl,
    "get_thread_last_node": get_thread_last_node_impl,
    "search_nodes": search_nodes_impl,
}

def get_previous_chunk_nodes_impl(book_id: str, **kwargs) -> list[dict]:
    # Query: SELECT id, timeline_anchor, thread_id, characters, narrative_role
    #         FROM nodes WHERE book_id=? AND parent_chunk_id=?
    #         ORDER BY beat_index
    # Returns last chunk's nodes
    pass

def get_thread_last_node_impl(book_id: str, thread_id: str, **kwargs) -> dict | None:
    # Find node in thread with no incoming thread_next_node_id
    # i.e., node X where no other node Y has Y.thread_next_node_id = X.id
    # Return X.id, X.timeline_anchor, X.beat_index
    pass

def search_nodes_impl(book_id: str, keyword: str, **kwargs) -> list[dict]:
    # Query: SELECT id, thread_id FROM nodes
    #         WHERE book_id=? AND characters LIKE '%keyword%'
    # Return list of (id, thread_id, scene[:50], characters)
    pass
```

## Error Handling

- If a tool returns empty (e.g., no previous chunk nodes exist): return `[]` or `null`, LLM handles gracefully
- If a tool name is unknown: return `{"error": "unknown tool"}`, LLM should not retry
- If SQLite query fails: return `{"error": "query failed"}`, LLM proceeds without tool context

## Open Questions / Future Extensions

1. **Convergence node thread_prev**: Currently a single `thread_prev_node_id` cannot represent multiple incoming thread links. Future work: add `thread_prev_node_ids: list[str]` to NarrativeNode.
2. **Vector search T4**: If "find scenes by emotional similarity" is needed for podcast material, add a fourth tool using the existing vector store.
3. **Tool call budget**: Limit max tool calls per generation (e.g., 5) to prevent infinite loops. Implement as: if tool_calls count > MAX_CALLS, break loop and return best-effort.
