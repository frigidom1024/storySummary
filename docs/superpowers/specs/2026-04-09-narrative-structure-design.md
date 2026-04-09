# Narrative Structure Design: Story Graph with Threads & Timeline

**Date:** 2026-04-09
**Status:** In Review

---

## 1. Overview

Extend NarrativeNode to support story graph visualization with:
1. **Multiple narrative threads** (story lines / branches)
2. **Timeline ordering** (story-chronological vs text-chronological)
3. **Convergence points** (where threads meet)

This enables:
- AI can query specific threads independently
- AI can output in true story-chronological order (for reverse-chronology stories)
- Visualization can render a story graph with branches and convergence

---

## 2. New Fields for NarrativeNode

### Timeline Coordinates

```python
timeline_order: int = 0      # Story-chronological order (integer, negative=before主线, positive=after)
timeline_anchor: str = ""  # Time label: "大学时期", "毕业后一年", "现在", "第一章"
is_time_jump: bool = False # Is this a time jump?
jump_direction: str = ""   # "past"=jump to past, "future"=jump to future
jump_label: str = ""        # "插叙", "倒叙", "前传", ""
```

### Thread (Story Line) Links

```python
thread_id: str = "main"      # Thread ID: "main"(默认主线), "zhang", "chenwei", "laozhou"
thread_name: str = ""         # Thread display name: "张医生的主线", "林夏情感线"
thread_prev_node_id: str = "" # Previous node in SAME thread (backward link)
thread_next_node_id: str = "" # Next node in SAME thread (forward link, optional for traversal)

# Branch/Convergence
branch_from_node: str = ""   # Node ID where this branch diverged from parent thread
converges_to_node: str = ""  # Node ID this thread converges to (optional)
is_convergence: bool = False # Is this a multi-thread convergence point?
```

---

## 3. Data Model

### Example: Multi-thread Story (3 threads)

```
原始文本顺序:
n-0-0 (张医生, 医院) → n-0-1 (陈薇, 写字楼) → n-0-2 (老周, 小区)
→ n-0-3 (张医生+家属) → n-0-4 (陈薇) → n-0-5 (老周+家人) → n-0-6 (三线汇聚)

存储结构:
thread: zhang
  n-0-0(thread_prev=) → n-0-3(thread_prev=n-0-0, converges_to=n-0-6)

thread: chenwei
  n-0-1(thread_prev=) → n-0-4(thread_prev=n-0-1, converges_to=n-0-6)

thread: laozhou
  n-0-2(thread_prev=) → n-0-5(thread_prev=n-0-2, converges_to=n-0-6)

convergence node: n-0-6
  is_convergence=True, characters=[张医生,陈薇,老周]
```

### Example: Reverse Chronology

```
原始文本顺序:
n-0-0 (现在, timeline_order=0) → n-0-1 (一年前, timeline_order=-12)
→ n-0-2 (两年半前, timeline_order=-30) → n-0-3 (三年前, timeline_order=-36)

所有节点 thread_id="main"

输出时: 按 timeline_order ASC 排列 → 三年前→一年前→现在（真实故事时间）
```

### Example: Flashback

```
n-0-0 (现在) → n-0-1 (回忆:外婆家, timeline_order=-20年)
  is_time_jump=True, jump_direction="past", jump_label="插叙"
```

---

## 4. Implementation

### 4.1 Model Changes

**File:** `src/models/narrative_node.py`

Add new fields to `NarrativeNode`:

```python
class NarrativeNode(BaseModel):
    # ... existing fields ...

    # === 时间坐标 ===
    timeline_order: int = 0
    timeline_anchor: str = ""
    is_time_jump: bool = False
    jump_direction: str = ""
    jump_label: str = ""

    # === 叙事线链路 ===
    thread_id: str = "main"
    thread_name: str = ""
    thread_prev_node_id: str = ""
    thread_next_node_id: str = ""
    branch_from_node: str = ""
    converges_to_node: str = ""
    is_convergence: bool = False
```

### 4.2 Prompt Changes

**File:** `src/core/prompts.py`

Update `MULTI_BEAT_NODE_PROMPT` to instruct LLM to generate:
- `timeline_order` (integer relative position)
- `timeline_anchor` (text label)
- `is_time_jump` + `jump_direction` + `jump_label`
- `thread_id` + `thread_name`
- `thread_prev_node_id` (link within same thread)
- `is_convergence` + `converges_to_node`

### 4.3 Generator Changes

**File:** `src/core/node_generator.py`

Update `NarrativeBeatModel` and mapping code to include new fields.

### 4.4 Story Graph Helper

**File:** `src/core/story_graph.py` (new)

A helper class to query and traverse the story graph:

```python
class StoryGraph:
    def __init__(self, nodes: list[NarrativeNode]):
        self.nodes = nodes
        self._node_map: dict[str, NarrativeNode] = {}
        self._thread_index: dict[str, list[NarrativeNode]] = {}  # thread_id -> nodes
        self._build_indices()

    def _build_indices(self):
        """Build lookup indices from nodes."""
        for node in self.nodes:
            self._node_map[node.id] = node
            if node.thread_id not in self._thread_index:
                self._thread_index[node.thread_id] = []
            self._thread_index[node.thread_id].append(node)

    def get_threads(self) -> list[str]:
        """Get all thread IDs in this story."""
        return list(self._thread_index.keys())

    def get_thread(self, thread_id: str) -> list[NarrativeNode]:
        """Get all nodes in a thread, in story order (via thread_prev_node_id chain)."""

    def get_text_order(self) -> list[NarrativeNode]:
        """Get all nodes in original text/chunk order (via prev_node_id chain)."""

    def get_timeline_order(self) -> list[NarrativeNode]:
        """Get all nodes sorted by story-chronological order (timeline_order ASC)."""

    def get_convergence_points(self) -> list[NarrativeNode]:
        """Get all multi-thread convergence nodes."""

    def get_node_by_id(self, node_id: str) -> NarrativeNode | None:
        """Lookup node by ID."""

    def get_nodes_for_character(self, character_name: str) -> list[NarrativeNode]:
        """Get all nodes where a character appears."""

    def get_character_threads(self, character_name: str) -> list[str]:
        """Get which threads a character appears in."""
```

---

## 5. Backward Compatibility

- All new fields have default values `""` or `0`
- Existing nodes in DB will have empty values — treat as single-thread, timeline_order=0
- Old pipeline code that doesn't reference new fields will continue to work

---

## 6. Design Decisions

| Decision | Choice | Reason |
|---------|--------|--------|
| Timeline unit | Integer `timeline_order` | LLM can't judge "months" precisely, only relative ordering |
| Thread linking | `thread_prev_node_id` + `thread_next_node_id` | Bidirectional per-thread linked list; forward link optional |
| Default thread | `thread_id="main"` | Empty string ambiguous; explicit "main" for primary story line |
| Convergence | `is_convergence` flag + `characters` | Multi-character nodes already capture who's present; add flag for explicit convergence |
| Branch origin | `branch_from_node` | Marks where a sub-thread diverged from main thread |
