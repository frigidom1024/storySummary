# Narrative Structure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.

**Goal:** Extend NarrativeNode with thread/timeline fields and add StoryGraph helper for multi-thread story querying.

**Architecture:** Add new Pydantic fields to NarrativeNode (backward compatible defaults). Update LLM prompt to generate new fields. Add StoryGraph class for querying threads, timeline, and convergence.

**Tech Stack:** Python, Pydantic, existing LangChain LLM pipeline.

---

## File Map

```
src/models/narrative_node.py     — add timeline + thread fields
src/core/prompts.py              — update MULTI_BEAT_NODE_PROMPT
src/core/node_generator.py       — update NarrativeBeatModel + mapping
src/core/story_graph.py          — NEW: StoryGraph helper class
tests/core/test_story_graph.py  — NEW: StoryGraph tests
tests/core/test_node_generator.py — update existing tests
```

---

## Chunk 1: Add fields to NarrativeNode model

**Files:**
- Modify: `src/models/narrative_node.py`

- [ ] **Step 1: Read current model**

Run: `cat src/models/narrative_node.py`

- [ ] **Step 2: Add new fields to NarrativeNode**

Add these fields after `prev_node_id` and before `to_dict()`:

```python
    # === 时间坐标 ===
    timeline_order: int = 0       # 故事时间顺序（负=回忆/前传，正=主线后）
    timeline_anchor: str = ""     # 时间锚点："大学时期", "毕业后一年", "现在"
    is_time_jump: bool = False   # 是否是时间跳跃
    jump_direction: str = ""     # "past"=跳到过去, "future"=跳到未来
    jump_label: str = ""         # "插叙", "倒叙", "前传", ""

    # === 叙事线链路 ===
    thread_id: str = "main"      # 叙事线ID："main", "zhang", "chenwei"
    thread_name: str = ""        # 叙事线名称："张医生的主线"
    thread_prev_node_id: str = ""  # 同一条叙事线上的前一个节点
    thread_next_node_id: str = ""  # 同一条叙事线上的下一个节点

    # === 分支/汇聚 ===
    branch_from_node: str = ""   # 从哪个节点分出这条支线
    converges_to_node: str = ""  # 汇聚到哪个节点
    is_convergence: bool = False # 是否是汇聚点
```

- [ ] **Step 3: Verify existing tests still pass**

Run: `pytest tests/models/ -v 2>/dev/null || echo "No tests in tests/models/"`

Since NarrativeNode has no dedicated test file, just verify no import errors:
Run: `python -c "from src.models.narrative_node import NarrativeNode; n = NarrativeNode(id='test'); print('OK:', n.thread_id)"`

- [ ] **Step 4: Commit**

```bash
git add src/models/narrative_node.py
git commit -m "feat: add timeline and thread fields to NarrativeNode"
```

---

## Chunk 2: Update node_generator — NarrativeBeatModel + mapping

**Files:**
- Modify: `src/core/node_generator.py`

- [ ] **Step 1: Read current NarrativeBeatModel (lines ~42-58)**

- [ ] **Step 2: Add new fields to NarrativeBeatModel**

Find the `NarrativeBeatModel` class and add these fields after `narrative_role`:

```python
    # === 时间坐标 ===
    timeline_order: int = Field(default=0, description="Story-chronological order: negative=before主线, positive=after主线")
    timeline_anchor: str = Field(default="", description="Time anchor: 大学时期/毕业后一年/现在/第一章 etc")
    is_time_jump: bool = Field(default=False, description="Is this a time jump?")
    jump_direction: str = Field(default="", description="past/future - direction of jump")
    jump_label: str = Field(default="", description="插叙/倒叙/前传/前传 or empty")

    # === 叙事线链路 ===
    thread_id: str = Field(default="main", description="Thread ID: main/zhang/chenwei/laozhou etc")
    thread_name: str = Field(default="", description="Thread display name")
    thread_prev_node_id: str = Field(default="", description="Previous node ID in same thread")
    thread_next_node_id: str = Field(default="", description="Next node ID in same thread (optional)")

    # === 分支/汇聚 ===
    branch_from_node: str = Field(default="", description="Node ID where this thread diverged")
    converges_to_node: str = Field(default="", description="Node ID this thread converges to")
    is_convergence: bool = Field(default=False, description="Is this a multi-thread convergence point?")
```

- [ ] **Step 3: Update the mapping in generate_from_chunk**

Find the `NarrativeNode(...)` construction (around line 114) and add:

```python
            node = NarrativeNode(
                # ... existing fields ...
                # === 时间坐标 ===
                timeline_order=beat_data.timeline_order,
                timeline_anchor=beat_data.timeline_anchor,
                is_time_jump=beat_data.is_time_jump,
                jump_direction=beat_data.jump_direction,
                jump_label=beat_data.jump_label,
                # === 叙事线链路 ===
                thread_id=beat_data.thread_id or "main",
                thread_name=beat_data.thread_name,
                thread_prev_node_id=beat_data.thread_prev_node_id,
                thread_next_node_id=beat_data.thread_next_node_id,
                # === 分支/汇聚 ===
                branch_from_node=beat_data.branch_from_node,
                converges_to_node=beat_data.converges_to_node,
                is_convergence=beat_data.is_convergence,
            )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/core/test_node_generator.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/core/node_generator.py
git commit -m "feat: add timeline and thread fields to NarrativeBeatModel"
```

---

## Chunk 3: Update prompts.py — instruct LLM to generate new fields

**Files:**
- Modify: `src/core/prompts.py`

- [ ] **Step 1: Read current MULTI_BEAT_NODE_PROMPT (lines 1-74)**

- [ ] **Step 2: Add new fields to the JSON schema in the prompt**

Find the JSON schema part in the prompt (around line 22-51) and add new fields. The current schema ends with `narrative_role`. Add these fields after `narrative_role`:

```json
    "timeline_order": 0,
    "timeline_anchor": "现在",
    "is_time_jump": false,
    "jump_direction": "",
    "jump_label": "",
    "thread_id": "main",
    "thread_name": "主线",
    "thread_prev_node_id": "",
    "thread_next_node_id": "",
    "branch_from_node": "",
    "converges_to_node": "",
    "is_convergence": false
```

- [ ] **Step 3: Add explanation section in the prompt**

Add this BEFORE the JSON schema, after the existing "## 输出格式" header:

```markdown
## 时间与叙事线标注规则

### 时间坐标
- `timeline_order`: 故事时间顺序（整数）。主线"现在"为0，过去为负（如-24），未来为正（如+3）。不需要精确月份，LLM只需判断相对顺序。
- `timeline_anchor`: 时间锚点文字："大学时期", "毕业后一年", "第一章", "现在" 等
- `is_time_jump`: 是否有时间跳跃（插叙/倒叙）
- `jump_direction`: past=跳到过去, future=跳到未来
- `jump_label`: 插叙/倒叙/前传/前传 或空

### 叙事线（Thread）
- `thread_id`: 叙事线ID，"main"=默认主线，其他如"zhang"(张医生线),"chenwei"(陈薇线),"laozhou"(老周线)
- `thread_name`: 叙事线名称，如"张医生的主线"
- `thread_prev_node_id`: 同一条叙事线上"前一个节点"的ID（用于链表链接）
- `thread_next_node_id`: 同一条叙事线上"后一个节点"的ID（可选）

### 分支与汇聚
- `is_convergence`: 这个节点是否是两条以上叙事线的汇聚点（如：多条线在同一场景交汇）
- `converges_to_node`: 如果是汇聚点，汇聚到哪个节点ID（可选）
- `branch_from_node`: 如果这是一个新分支的起点，从哪个节点分出

### 示例

**单线倒叙（timeline_order）：**
```json
{
  "id": "n-0-0",
  "timeline_order": 0,
  "timeline_anchor": "现在",
  "is_time_jump": true,
  "jump_direction": "past",
  "jump_label": "倒叙",
  "thread_id": "main",
  "thread_prev_node_id": ""
}
```

**多线叙事（thread_id）：**
```json
{
  "id": "n-0-0",
  "thread_id": "zhang",
  "thread_name": "张医生线",
  "thread_prev_node_id": ""
}
```

**汇聚点：**
```json
{
  "id": "n-0-6",
  "is_convergence": true,
  "characters": [{"name": "张医生"}, {"name": "陈薇"}, {"name": "老周"}]
}
```
```

- [ ] **Step 4: Verify import still works**

Run: `python -c "from src.core.prompts import MULTI_BEAT_NODE_PROMPT; print('OK, len:', len(MULTI_BEAT_NODE_PROMPT))"`

- [ ] **Step 5: Commit**

```bash
git add src/core/prompts.py
git commit -m "feat: add timeline and thread field instructions to MULTI_BEAT_NODE_PROMPT"
```

---

## Chunk 4: Create StoryGraph helper class

**Files:**
- Create: `src/core/story_graph.py`
- Create: `tests/core/test_story_graph.py`

### Part A: Write the failing test first

- [ ] **Step 1: Create test file**

Create `tests/core/test_story_graph.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.core.story_graph import StoryGraph
from src.models.narrative_node import NarrativeNode, CharacterState


def make_node(node_id: str, thread_id: str = "main", timeline_order: int = 0,
              prev: str = "", next_n: str = "",
              is_conv: bool = False, chars: list[str] = None) -> NarrativeNode:
    """Helper to create a test node."""
    return NarrativeNode(
        id=node_id,
        thread_id=thread_id,
        thread_name=f"{thread_id}线",
        timeline_order=timeline_order,
        thread_prev_node_id=prev,
        thread_next_node_id=next_n,
        is_convergence=is_conv,
        characters=[CharacterState(name=c) for c in (chars or [])],
        scene=f"场景-{node_id}",
        situation=f"情境-{node_id}",
        narrative_role="rising"
    )


def test_get_threads():
    """Test get_threads returns all thread IDs."""
    nodes = [
        make_node("n-0", thread_id="main"),
        make_node("n-1", thread_id="zhang"),
        make_node("n-2", thread_id="chenwei"),
    ]
    sg = StoryGraph(nodes)
    threads = sg.get_threads()
    assert set(threads) == {"main", "zhang", "chenwei"}


def test_get_thread_main():
    """Test get_thread returns nodes in story order."""
    # n-0 → n-3 (main thread)
    # n-1 → n-4 (zhang thread)
    nodes = [
        make_node("n-0", thread_id="main", timeline_order=0),
        make_node("n-1", thread_id="main", timeline_order=1, prev="n-0"),
        make_node("n-3", thread_id="main", timeline_order=2, prev="n-1"),
    ]
    sg = StoryGraph(nodes)
    thread_nodes = sg.get_thread("main")
    ids = [n.id for n in thread_nodes]
    assert ids == ["n-0", "n-1", "n-3"]


def test_get_timeline_order():
    """Test get_timeline_order sorts by timeline_order ASC."""
    nodes = [
        make_node("n-2", timeline_order=5),
        make_node("n-0", timeline_order=-10),
        make_node("n-1", timeline_order=0),
    ]
    sg = StoryGraph(nodes)
    ordered = sg.get_timeline_order()
    ids = [n.id for n in ordered]
    assert ids == ["n-0", "n-1", "n-2"]  # -10 → 0 → 5


def test_get_convergence_points():
    """Test get_convergence_points returns is_convergence nodes."""
    nodes = [
        make_node("n-0", is_conv=False),
        make_node("n-1", is_conv=True),
        make_node("n-2", is_conv=True),
    ]
    sg = StoryGraph(nodes)
    conv = sg.get_convergence_points()
    assert len(conv) == 2


def test_get_nodes_for_character():
    """Test get_nodes_for_character."""
    nodes = [
        make_node("n-0", chars=["林夏"]),
        make_node("n-1", chars=["林夏", "陈远"]),
        make_node("n-2", chars=["张博"]),
    ]
    sg = StoryGraph(nodes)
    linxia_nodes = sg.get_nodes_for_character("林夏")
    assert len(linxia_nodes) == 2


def test_get_character_threads():
    """Test get_character_threads returns which threads a character is on."""
    nodes = [
        make_node("n-0", thread_id="main", chars=["林夏"]),
        make_node("n-1", thread_id="zhang", chars=["林夏"]),  # 林夏 also appears on zhang thread
    ]
    sg = StoryGraph(nodes)
    threads = sg.get_character_threads("林夏")
    assert set(threads) == {"main", "zhang"}


def test_get_node_by_id():
    """Test get_node_by_id returns correct node."""
    nodes = [make_node("n-99")]
    sg = StoryGraph(nodes)
    n = sg.get_node_by_id("n-99")
    assert n is not None
    assert n.id == "n-99"
    assert sg.get_node_by_id("nonexistent") is None


def test_single_thread_default():
    """Single thread story with default thread_id=main."""
    nodes = [
        make_node("n-0", thread_id="main", timeline_order=0),
        make_node("n-1", thread_id="main", timeline_order=1, prev="n-0"),
    ]
    sg = StoryGraph(nodes)
    assert sg.get_threads() == ["main"]
    assert len(sg.get_thread("main")) == 2
```

- [ ] **Step 2: Run tests — verify they fail (module not found)**

Run: `pytest tests/core/test_story_graph.py -v`
Expected: FAIL — module not found

### Part B: Write the implementation

- [ ] **Step 3: Create StoryGraph class**

Create `src/core/story_graph.py`:

```python
"""Story graph helper for querying multi-thread narratives."""
from src.models.narrative_node import NarrativeNode


class StoryGraph:
    """
    Helper class to query and traverse a story graph with multiple threads.

    Supports:
    - Get all threads (story lines)
    - Get nodes in a specific thread (via thread_prev_node_id chain)
    - Get nodes in original text order (via prev_node_id chain)
    - Get nodes in story-chronological order (timeline_order)
    - Get convergence points
    - Query by character
    """

    def __init__(self, nodes: list[NarrativeNode]):
        self.nodes = nodes
        self._node_map: dict[str, NarrativeNode] = {}
        self._thread_index: dict[str, list[NarrativeNode]] = {}
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
        """
        Get all nodes in a thread, in story order (via thread_prev_node_id chain).

        Traverses using thread_prev_node_id links. If no links exist,
        falls back to chunk order.
        """
        thread_nodes = self._thread_index.get(thread_id, [])
        if not thread_nodes:
            return []

        # Find the head (node with empty thread_prev_node_id)
        head = None
        for n in thread_nodes:
            if not n.thread_prev_node_id:
                head = n
                break

        if not head:
            # No links found, return in chunk order
            return sorted(thread_nodes, key=lambda n: n.beat_index)

        # Traverse via thread_prev_node_id links
        result = []
        current = head
        while current:
            result.append(current)
            # Find next via thread_next_node_id first (forward link)
            if current.thread_next_node_id:
                current = self._node_map.get(current.thread_next_node_id)
            else:
                # Fall back: find node whose thread_prev_node_id == current.id
                current = None
                for n in thread_nodes:
                    if n.thread_prev_node_id == result[-1].id and n not in result:
                        current = n
                        break

        return result

    def get_text_order(self) -> list[NarrativeNode]:
        """
        Get all nodes in original text/chunk order (via prev_node_id chain).
        """
        if not self.nodes:
            return []

        # Find head (node with empty prev_node_id)
        head = None
        for n in self.nodes:
            if not n.prev_node_id:
                head = n
                break

        if not head:
            return list(self.nodes)

        # Traverse via prev_node_id links
        result = []
        current = head
        visited = set()
        while current and current.id not in visited:
            result.append(current)
            visited.add(current.id)
            current = self._node_map.get(current.prev_node_id) if current.prev_node_id else None

        return result

    def get_timeline_order(self) -> list[NarrativeNode]:
        """
        Get all nodes sorted by story-chronological order (timeline_order ASC).
        For same timeline_order, preserve relative order.
        """
        return sorted(self.nodes, key=lambda n: (n.timeline_order, n.beat_index))

    def get_convergence_points(self) -> list[NarrativeNode]:
        """Get all multi-thread convergence nodes."""
        return [n for n in self.nodes if n.is_convergence]

    def get_node_by_id(self, node_id: str) -> NarrativeNode | None:
        """Lookup node by ID."""
        return self._node_map.get(node_id)

    def get_nodes_for_character(self, character_name: str) -> list[NarrativeNode]:
        """Get all nodes where a character appears."""
        return [
            n for n in self.nodes
            if any(c.name == character_name for c in n.characters)
        ]

    def get_character_threads(self, character_name: str) -> list[str]:
        """Get which threads a character appears in."""
        threads = set()
        for n in self.nodes:
            if any(c.name == character_name for c in n.characters):
                threads.add(n.thread_id)
        return list(threads)
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `pytest tests/core/test_story_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/story_graph.py tests/core/test_story_graph.py
git commit -m "feat: add StoryGraph helper for multi-thread story querying"
```

---

## Chunk 5: Update existing tests for backward compatibility

**Files:**
- Modify: `tests/core/test_node_generator.py`

- [ ] **Step 1: Read current test file**

The test uses `NarrativeNode` with fields that still exist. We need to ensure the new fields don't break existing tests.

- [ ] **Step 2: Run existing tests**

Run: `pytest tests/core/test_node_generator.py -v`

If they pass, no changes needed (backward compatible defaults).

- [ ] **Step 3: Commit (only if changes were needed)**

```bash
git add tests/core/test_node_generator.py  # only if changed
git commit -m "test: ensure node_generator tests pass with new fields"
```

---

## Verification

After all chunks:

```bash
# Run all tests
pytest tests/ -v

# Smoke test new fields
python -c "
from src.models.narrative_node import NarrativeNode
n = NarrativeNode(id='test', thread_id='main', timeline_order=-10)
assert n.thread_id == 'main'
assert n.timeline_order == -10
print('Model fields OK')

from src.core.story_graph import StoryGraph
print('StoryGraph import OK')
"
```

---

## Dependency Order

1. Chunk 1: Model fields (no dependencies)
2. Chunk 2: Generator (depends on model)
3. Chunk 3: Prompts (depends on nothing)
4. Chunk 4: StoryGraph (depends on model)
5. Chunk 5: Tests (verify nothing broke)
