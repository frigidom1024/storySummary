# 分阶段节点生成实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将节点生成拆分为三阶段（Agent1内容 + Agent2/3结构 + CharacterTracker角色追踪），降低单次LLM调用复杂度，减少幻觉。

**Architecture:** Agent1负责语义内容，Agent2+Agent3（绑定）负责时间/结构，CharacterTracker程序化处理角色累积。各阶段职责单一，通过滑动上下文传递。

**Tech Stack:** Python async/await, Pydantic, LangChain

## 审查后修订（2026-04-13）

为保证可执行与兼容现有系统，实施时按以下修订落地：

1. `NarrativeNodeGenerator.generate_from_chunk` **保持返回 `list[NarrativeNode]`**，不改为 tuple，避免破坏 `pipeline/analyzer` 现有调用。
2. CharacterTracker 改为 **生成器实例级持久对象**（跨 chunk 累积），不在每次 chunk 内部新建。
3. Agent2 异步测试统一使用 `pytest.mark.asyncio + await`。
4. 新增 prompts（`time_anchor` / `graph_builder_prompt`）后，必须同步更新 `src/prompts/__init__.py` 导出。
5. CharacterTracker 交互来源采用“当前节点首个角色”最小规则，替代计划草案中的 `return None` 占位实现，确保测试与行为一致。

---

## Chunk 1: 模型修改

**Files:**
- Modify: `src/models/narrative_node.py` - 修改 importance 字段 + 添加 interactions
- Test: `tests/models/test_narrative_node.py`

- [ ] **Step 1: 创建测试文件**

Run: `mkdir -p tests/models && touch tests/models/__init__.py tests/models/test_narrative_node.py`

```python
# tests/models/test_narrative_node.py
import pytest
from src.models.narrative_node import NarrativeNode, CharacterState, InteractionModel

def test_importance_normalized_to_float():
    """importance 应为 0.0-1.0 范围的 float"""
    node = NarrativeNode(id="n-0-0", importance=0.75)
    assert isinstance(node.importance, float)
    assert 0.0 <= node.importance <= 1.0

def test_importance_defaults():
    """importance 默认 0.5（普通）"""
    node = NarrativeNode(id="n-0-0")
    assert node.importance == 0.5

def test_interactions_field():
    """节点应支持 interactions 字段"""
    node = NarrativeNode(
        id="n-0-0",
        interactions=[
            InteractionModel(target="老板", type="tension", intensity_delta=0.3)
        ]
    )
    assert len(node.interactions) == 1
    assert node.interactions[0].target == "老板"
    assert node.interactions[0].intensity_delta == 0.3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/models/test_narrative_node.py -v`
Expected: FAIL - NarrativeNode 没有 interactions 字段，importance 不是 float

- [ ] **Step 3: 修改 NarrativeNode 模型**

```python
# src/models/narrative_node.py
from pydantic import BaseModel, Field
from typing import Optional

class InteractionModel(BaseModel):
    """角色交互感知（Agent1输出）"""
    target: str = Field(description="交互对象角色名")
    type: str = Field(description="交互类型: tension/support/neutral")
    intensity_delta: float = Field(description="强度变化 -1.0到1.0")

class CharacterState(BaseModel):
    """角色在该节点进入时的状态"""
    name: str
    state_before: str = ""

class RelationshipStateChange(BaseModel):
    """一对角色在该节点中的关系变化"""
    pair: str = ""
    from_state: str = ""
    to_state: str = ""

class NarrativeNode(BaseModel):
    id: str
    parent_chunk_id: str = ""
    beat_index: int = 0
    scene: str = ""
    location: str = ""
    scene_timing: str = ""
    characters: list[CharacterState] = Field(default_factory=list)
    situation: str = ""
    turning_point: str = ""
    importance: float = Field(default=0.5, description="节点重要性: 0.0-1.0, 0.3-0.5普通, 0.6-0.8重要, 0.8-1.0关键")
    emotional_arc: str = ""
    mood_tone: str = ""
    narrative_rhythm: str = ""
    discussion_prompts: list[str] = Field(default_factory=list)
    relationship_delta: list[RelationshipStateChange] = Field(default_factory=list)
    interactions: list[InteractionModel] = Field(default_factory=list, description="Agent1输出的交互感知")
    prev_node_id: str = ""
    narrative_role: str = ""
    timeline_order: int = 0
    timeline_anchor: str = ""
    is_time_jump: bool = False
    jump_direction: str = ""
    jump_label: str = ""
    thread_id: str = "main"
    thread_name: str = ""
    thread_prev_node_id: str = ""
    thread_next_node_id: str = ""
    branch_from_node: str = ""
    converges_to_node: str = ""
    is_convergence: bool = False

    def to_dict(self) -> dict:
        return self.model_dump()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/models/test_narrative_node.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/models/narrative_node.py tests/models/test_narrative_node.py
git commit -m "feat(models): normalize importance to 0.0-1.0 float and add interactions field"
```

---

## Chunk 2: CharacterCard 模型

**Files:**
- Create: `src/models/character_card.py` - CharacterTracker 用的人物卡片模型
- Test: `tests/models/test_character_card.py`

- [ ] **Step 1: 创建测试**

```python
# tests/models/test_character_card.py
import pytest
from src.models.character_card import CharacterCard, Relationship, EmotionalSnapshot

def test_create_character_card():
    card = CharacterCard(character_id="陈屿", name="陈屿", first_seen="n-0-0", current_state="无聊")
    assert card.total_appearances == 0
    assert card.relationships == {}
    assert card.emotional_timeline == []

def test_update_relationship():
    card = CharacterCard(character_id="陈屿", name="陈屿", first_seen="n-0-0")
    card.add_interaction("老板", "tension", 0.3, "n-0-1")
    assert "老板" in card.relationships
    assert card.relationships["老板"].current_intensity == 0.3

def test_emotional_timeline_append():
    card = CharacterCard(character_id="陈屿", name="陈屿", first_seen="n-0-0")
    card.update_emotional_state("无聊", "n-0-0")
    card.update_emotional_state("微妙", "n-1-1")
    assert len(card.emotional_timeline) == 2
    assert card.emotional_timeline[1].emotion == "微妙"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/models/test_character_card.py -v`
Expected: FAIL - module not found

- [ ] **Step 3: 创建 CharacterCard 模型**

```python
# src/models/character_card.py
from pydantic import BaseModel, Field
from typing import Dict, List

class Relationship(BaseModel):
    """角色关系"""
    type: str = Field(description="关系类型: tension/support/neutral")
    current_intensity: float = Field(default=0.0, description="当前关系强度 0.0-1.0")
    history: List[dict] = Field(default_factory=list, description="关系变化历史")

class EmotionalSnapshot(BaseModel):
    """情绪快照"""
    node_id: str
    emotion: str

class CharacterCard(BaseModel):
    """人物卡片 - CharacterTracker维护"""
    character_id: str
    name: str
    first_seen: str = ""
    current_state: str = ""
    total_appearances: int = 0
    relationships: Dict[str, Relationship] = Field(default_factory=dict)
    emotional_timeline: List[EmotionalSnapshot] = Field(default_factory=list)
    key_events: List[str] = Field(default_factory=list)

    def add_interaction(self, target: str, interaction_type: str, intensity_delta: float, node_id: str):
        """从 interactions 累积关系变化"""
        if target not in self.relationships:
            self.relationships[target] = Relationship(type=interaction_type)
        rel = self.relationships[target]
        rel.current_intensity = max(0.0, min(1.0, rel.current_intensity + intensity_delta))
        rel.history.append({"node_id": node_id, "intensity": rel.current_intensity})

    def update_emotional_state(self, emotion: str, node_id: str):
        """从 emotional_arc 累积情绪状态"""
        self.current_state = emotion
        self.emotional_timeline.append(EmotionalSnapshot(node_id=node_id, emotion=emotion))

    def increment_appearance(self):
        self.total_appearances += 1

    def add_key_event(self, node_id: str):
        if node_id not in self.key_events:
            self.key_events.append(node_id)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/models/test_character_card.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/models/character_card.py tests/models/test_character_card.py
git commit -m "feat(models): add CharacterCard for CharacterTracker"
```

---

## Chunk 3: Agent1 Prompt 扩展

**Files:**
- Modify: `src/prompts/base_node.py` - 扩展 BASE_NODE_PROMPT
- Test: `tests/core/test_node_generator.py` - 已有测试

- [ ] **Step 1: 读取现有 prompt 并规划修改**

```python
# 需要修改的内容：
# 1. 添加 interactions 字段到输出
# 2. importance 改为 0.0-1.0 范围
# 3. 添加 last_nodes 上下文输入支持
```

- [ ] **Step 2: 修改 base_node.py**

```python
# src/prompts/base_node.py
BASE_NODE_PROMPT = """你是一个专业的小说场记师。你的任务是从文本中提取叙事原子（Beat），只关注内容，不关注结构。

## 什么是叙事原子（Beat）

叙事原子是故事的最小单元：
- 同一场景（时间+地点不变）
- 同一组人物在场
- 一个完整的情感转折或事件推进

## 内容字段

每个节点提取以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| id | 节点ID，格式 n-{chunk_order}-{beat_index} | n-0-0 |
| beat_index | 在本chunk内的顺序，从0开始 | 0 |
| scene | 完整场景描述 | 青岛路旧书店，下午三点多 |
| location | 简化地点名 | 青岛路旧书店 |
| scene_timing | 时间段 | 午后 |
| characters | 在场角色列表 | [{"name": "陈屿", "state_before": "无聊"}] |
| situation | 一句话情况描述，不超过25字 | 陈屿需要一个不被打扰的地方 |
| turning_point | 核心变化 | 他发现扉页有签名的《围城》 |
| emotional_arc | 情绪弧线 | 陈屿从'无所谓'到'想要拥有' |
| mood_tone | 氛围关键词，3个 | 慵懒, 偶然, 微妙 |
| narrative_rhythm | 叙事节奏 | slow/steady/fast/pause |
| importance | 重要性 0.0-1.0 | 0.75 |
| interactions | 交互感知（见下方） | 见下方 |

## importance 判断标准

- 0.3-0.5（普通）: 日常过渡场景，不影响主线
- 0.6-0.8（重要）: 有情感变化、冲突、决策的场景
- 0.8-1.0（关键）: 核心转折点、重大发现、人物命运改变

## interactions 字段

每个角色最多 2 个 interaction，超出忽略：

```json
{
  "target": "对方角色名",
  "type": "tension | support | neutral",
  "intensity_delta": -1.0到1.0（变化量）
}
```

## 上一个 chunk 的上下文（参考）

{last_nodes}

## 输出格式

直接输出JSON数组，不要解释：

```json
[
  {
    "id": "n-{chunk_order}-0",
    "beat_index": 0,
    "scene": "场景描述",
    "location": "简化地点",
    "scene_timing": "时间段",
    "characters": [{"name": "角色名", "state_before": "进入时的状态"}],
    "situation": "一句话情况描述",
    "turning_point": "核心变化",
    "emotional_arc": "角色从[X]到[Y]",
    "mood_tone": "氛围1, 氛围2, 氛围3",
    "narrative_rhythm": "steady",
    "importance": 0.5,
    "interactions": [
      {"target": "对方角色", "type": "tension", "intensity_delta": 0.3}
    ]
  }
]
```

Text to analyze:
{text}"""

# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("base_node", BASE_NODE_PROMPT)
```

- [ ] **Step 3: 提交**

```bash
git add src/prompts/base_node.py
git commit -m "feat(prompts): extend Agent1 prompt with interactions and 0.0-1.0 importance"
```

---

## Chunk 4: Agent2 TimeAnchorResolver

**Files:**
- Create: `src/core/time_anchor_resolver.py` - Agent2 实现
- Create: `src/prompts/time_anchor.py` - Agent2 prompt
- Test: `tests/core/test_time_anchor_resolver.py`

- [ ] **Step 1: 创建 Agent2 prompt**

```python
# src/prompts/time_anchor.py

TIME_ANCHOR_PROMPT = """你是一个时间分析师。你的任务是为每个叙事节点判断时间位置。

## 输入

每个节点的结构：
- node_id: 节点ID
- scene: 场景描述
- timeline_anchor: 上一个chunk的时间锚点（参考）

## 输出要求

为每个节点输出时间判断：

```json
[
  {
    "node_id": "n-1-0",
    "time_type": "present | past | future",
    "relative_to_prev": "continue | jump | unclear",
    "anchor_hint": "大学时期",
    "confidence": 0.9
  }
]
```

## 判断标准

- time_type:
  - present: 当前主线时间
  - past: 回忆/倒叙
  - future: 预叙/未来

- relative_to_prev:
  - continue: 时间自然推进（下午→傍晚，同一地点连续）
  - jump: 时间跳跃（回忆、插叙、时间线切换）
  - unclear: 无法判断

## 注意事项

- 批量处理所有节点，保证一致性
- 参考 last_timeline_state 判断是否延续
- confidence 低于 0.6 时用 unclear

Context from previous chunk:
{last_timeline_state}

Nodes to analyze:
{nodes}

Output JSON array:"""

from .registry import global_registry
global_registry.register("time_anchor", TIME_ANCHOR_PROMPT)
```

- [ ] **Step 2: 创建 TimeAnchorResolver 类**

```python
# src/core/time_anchor_resolver.py
import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts import TIME_ANCHOR_PROMPT
from src.logging_config import debug

logger = logging.getLogger("story-summary")

class TimeAnchorResult(BaseModel):
    """Agent2 输出"""
    node_id: str
    time_type: str = Field(description="present/past/future")
    relative_to_prev: str = Field(description="continue/jump/unclear")
    anchor_hint: str = ""
    confidence: float = 0.5

def create_time_anchor_llm() -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=0.3,
        openai_api_base=api_base or "https://api.deepseek.com/v1"
    )

class TimeAnchorResolver:
    """Agent2: 时间锚定"""

    def __init__(self, api_key: str = None):
        self.llm = create_time_anchor_llm() if api_key or os.getenv("DEEPSEEK_API_KEY") else None

    async def resolve(self, nodes: list, last_timeline_state: dict = None) -> list[TimeAnchorResult]:
        """批量处理节点的时间判断"""
        if self.llm is None:
            # 返回默认值
            return [
                TimeAnchorResult(node_id=n["id"], time_type="present", relative_to_prev="continue", confidence=0.5)
                for n in nodes
            ]

        last_state_str = json.dumps(last_timeline_state or {}, ensure_ascii=False)
        nodes_str = json.dumps(nodes, ensure_ascii=False)

        prompt = TIME_ANCHOR_PROMPT.format(
            last_timeline_state=last_state_str,
            nodes=nodes_str
        )

        messages = [
            SystemMessage(content="You are a time analyst. Output ONLY JSON array."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') and response.content else "[]"

        try:
            results = json.loads(content)
            return [TimeAnchorResult(**r) for r in results]
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse TimeAnchorResult: {content[:200]}")
            return [
                TimeAnchorResult(node_id=n["id"], time_type="present", relative_to_prev="continue", confidence=0.5)
                for n in nodes
            ]
```

- [ ] **Step 3: 创建测试**

```python
# tests/core/test_time_anchor_resolver.py
import pytest
from src.core.time_anchor_resolver import TimeAnchorResolver, TimeAnchorResult

@pytest.fixture
def resolver():
    return TimeAnchorResolver()

def test_time_anchor_result_model():
    result = TimeAnchorResult(
        node_id="n-0-0",
        time_type="present",
        relative_to_prev="continue",
        anchor_hint="现在",
        confidence=0.9
    )
    assert result.node_id == "n-0-0"
    assert result.time_type == "present"

def test_resolver_returns_defaults_without_llm(resolver):
    nodes = [{"id": "n-0-0", "scene": "test"}]
    results = resolver.resolve(nodes)
    assert len(results) == 1
    assert results[0].node_id == "n-0-0"
    assert results[0].time_type == "present"
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/core/test_time_anchor_resolver.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/time_anchor_resolver.py src/prompts/time_anchor.py tests/core/test_time_anchor_resolver.py
git commit -m "feat(core): add TimeAnchorResolver (Agent2)"
```

---

## Chunk 5: Agent3 GraphBuilder

**Files:**
- Create: `src/core/graph_builder.py` - Agent3 混合架构
- Create: `src/prompts/graph_builder_prompt.py` - Agent3 LLM 部分
- Test: `tests/core/test_graph_builder.py`

- [ ] **Step 1: 创建 Agent3 prompt**

```python
# src/prompts/graph_builder_prompt.py

GRAPH_BUILDER_PROMPT = """你是一个叙事结构分析师。你的任务是基于角色重叠度判断thread方向。

## 输入

- nodes: 当前chunk的节点（含Agent1内容 + Agent2时间）
- recent_nodes: 最近5个节点（id, characters, thread_id）
- thread_summaries: 各thread的角色列表

## 输出要求

为每个节点输出thread_hint：

```json
[
  {
    "node_id": "n-1-0",
    "thread_hint": "main | new | uncertain",
    "link_confidence": 0.6
  }
]
```

## 判断标准

- thread_hint:
  - main: 延续主线叙事
  - new: 新开一条叙事线
  - uncertain: 不确定

- link_confidence: 0.0-1.0，越高越确定

## 注意事项

- 每次处理当前chunk的节点，不处理历史
- 基于角色重叠度判断是否延续thread
- 如果角色与任何现有thread重叠 > 50%，归属该thread
- 否则考虑新开thread

Current nodes:
{nodes}

Recent nodes (last 5):
{recent_nodes}

Thread summaries:
{thread_summaries}

Output JSON array:"""

from .registry import global_registry
global_registry.register("graph_builder", GRAPH_BUILDER_PROMPT)
```

- [ ] **Step 2: 创建 GraphBuilder 类**

```python
# src/core/graph_builder.py
import os
import json
import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts import GRAPH_BUILDER_PROMPT
from src.logging_config import debug

logger = logging.getLogger("story-summary")

class GraphBuilderResult(BaseModel):
    """Agent3 输出"""
    node_id: str
    thread_hint: str = Field(description="main/new/uncertain")
    link_confidence: float = 0.5

class ThreadState:
    """程序维护的thread状态"""
    def __init__(self):
        self.threads: dict[str, set[str]] = {}  # thread_id -> set of character names
        self.last_node_in_thread: dict[str, str] = {}  # thread_id -> last node_id

    def add_thread(self, thread_id: str, characters: list[str]):
        if thread_id not in self.threads:
            self.threads[thread_id] = set()
        self.threads[thread_id].update(characters)

    def get_thread_characters(self, thread_id: str) -> set:
        return self.threads.get(thread_id, set())

    def set_last_node(self, thread_id: str, node_id: str):
        self.last_node_in_thread[thread_id] = node_id

    def get_last_node(self, thread_id: str) -> Optional[str]:
        return self.last_node_in_thread.get(thread_id)

    def find_best_thread(self, characters: list[str]) -> Optional[tuple[str, float]]:
        """基于角色重叠度找最佳thread"""
        best = None
        best_overlap = 0
        for thread_id, thread_chars in self.threads.items():
            overlap = len(set(characters) & thread_chars)
            if overlap > best_overlap:
                best_overlap = overlap
                best = thread_id
        if best and best_overlap > 0:
            return best, best_overlap / len(characters)
        return None, 0.0

def create_graph_builder_llm() -> ChatOpenAI:
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE")
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        temperature=0.3,
        openai_api_base=api_base or "https://api.deepseek.com/v1"
    )

class GraphBuilder:
    """Agent3: 结构层 - 混合架构"""

    def __init__(self, api_key: str = None):
        self.llm = create_graph_builder_llm() if api_key or os.getenv("DEEPSEEK_API_KEY") else None
        self.thread_state = ThreadState()

    def get_context_summary(self) -> dict:
        """获取Agent3需要的上下文摘要"""
        recent = []
        for thread_id, last_node in list(self.thread_state.last_node_in_thread.items())[-5:]:
            recent.append({
                "id": last_node,
                "characters": list(self.thread_state.get_thread_characters(thread_id)),
                "thread_id": thread_id
            })
        return {
            "recent_nodes": recent,
            "thread_summaries": {tid: list(chars) for tid, chars in self.thread_state.threads.items()}
        }

    async def build(self, nodes: list, time_anchors: list, thread_enabled: bool = True) -> list[dict]:
        """构建thread结构"""
        if not thread_enabled or self.llm is None:
            return self._build_with_defaults(nodes)

        context = self.get_context_summary()
        prompt = GRAPH_BUILDER_PROMPT.format(
            nodes=json.dumps(nodes, ensure_ascii=False),
            recent_nodes=json.dumps(context["recent_nodes"], ensure_ascii=False),
            thread_summaries=json.dumps(context["thread_summaries"], ensure_ascii=False)
        )

        messages = [
            SystemMessage(content="You are a narrative structure analyst. Output ONLY JSON array."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        content = response.content if hasattr(response, 'content') and response.content else "[]"

        try:
            results = json.loads(content)
            return self._merge_with_program(nodes, time_anchors, results)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse GraphBuilderResult: {content[:200]}")
            return self._build_with_defaults(nodes)

    def _merge_with_program(self, nodes: list, time_anchors: list, llm_results: list) -> list[dict]:
        """混合架构：LLM给hint，程序执行"""
        result_map = {r["node_id"]: r for r in llm_results}

        for i, node in enumerate(nodes):
            node_id = node["id"]
            characters = [c["name"] for c in node.get("characters", [])]
            time_info = time_anchors[i] if i < len(time_anchors) else {}

            # 程序计算 timeline_order
            timeline_order = self._calc_timeline_order(node, time_info)

            # 程序分配 thread
            thread_id, thread_hint = self._assign_thread(node, result_map.get(node_id, {}), characters)

            # 查找 prev_node
            prev_node_id = self.thread_state.get_last_node(thread_id) or ""

            # 更新 thread_state
            self.thread_state.add_thread(thread_id, characters)
            self.thread_state.set_last_node(thread_id, node_id)

            node["timeline_order"] = timeline_order
            node["thread_id"] = thread_id
            node["thread_hint"] = thread_hint
            node["thread_prev_node_id"] = prev_node_id

        return nodes

    def _calc_timeline_order(self, node: dict, time_info: dict) -> int:
        """timeline_order 计算（限制层级深度 ∈ [-2, +2]）"""
        relative = time_info.get("relative_to_prev", "continue")
        time_type = time_info.get("time_type", "present")

        # 获取当前thread的最后timeline_order
        thread_id = node.get("thread_id", "main")
        # 默认0，在范围内即可
        return 0

    def _assign_thread(self, node: dict, llm_hint: dict, characters: list[str]) -> tuple[str, str]:
        """thread分配（基于角色重叠度）"""
        hint = llm_hint.get("thread_hint", "main")
        confidence = llm_hint.get("link_confidence", 0.5)

        if hint == "new" or not characters:
            # 新开thread
            thread_id = f"thread_{len(self.thread_state.threads)}"
            return thread_id, hint

        # 基于角色重叠度找最佳thread
        best_thread, overlap_ratio = self.thread_state.find_best_thread(characters)

        if overlap_ratio >= 0.5:
            return best_thread, "main"

        # 新开thread
        thread_id = f"thread_{len(self.thread_state.threads)}"
        return thread_id, hint

    def _build_with_defaults(self, nodes: list) -> list[dict]:
        """不使用LLM时的默认构建"""
        for node in nodes:
            node["timeline_order"] = 0
            node["thread_id"] = "main"
            node["thread_hint"] = "main"
            node["thread_prev_node_id"] = ""
        return nodes
```

- [ ] **Step 3: 创建测试**

```python
# tests/core/test_graph_builder.py
import pytest
from src.core.graph_builder import GraphBuilder, ThreadState, GraphBuilderResult

def test_thread_state():
    state = ThreadState()
    state.add_thread("main", ["陈屿", "老板"])
    state.set_last_node("main", "n-0-0")

    assert "陈屿" in state.get_thread_characters("main")
    assert state.get_last_node("main") == "n-0-0"

def test_find_best_thread():
    state = ThreadState()
    state.add_thread("main", ["陈屿", "老板"])
    state.add_thread("zhang", ["张医生"])

    best, ratio = state.find_best_thread(["陈屿", "老板"])
    assert best == "main"
    assert ratio > 0.5

def test_graph_builder_defaults():
    builder = GraphBuilder()
    nodes = [{"id": "n-0-0", "characters": [{"name": "陈屿"}]}]
    results = builder._build_with_defaults(nodes)
    assert results[0]["thread_id"] == "main"
    assert results[0]["timeline_order"] == 0
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/core/test_graph_builder.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/graph_builder.py src/prompts/graph_builder_prompt.py tests/core/test_graph_builder.py
git commit -m "feat(core): add GraphBuilder (Agent3) with hybrid architecture"
```

---

## Chunk 6: CharacterTracker

**Files:**
- Create: `src/core/character_tracker.py` - CharacterTracker 实现
- Test: `tests/core/test_character_tracker.py`

- [ ] **Step 1: 创建 CharacterTracker**

```python
# src/core/character_tracker.py
import logging
from typing import Dict, Optional
from src.models.character_card import CharacterCard

logger = logging.getLogger("story-summary")

class CharacterTracker:
    """角色追踪器 - 从Agent1 nodes实时构建人物卡片"""

    def __init__(self):
        self.characters: Dict[str, CharacterCard] = {}

    def process_nodes(self, nodes: list):
        """处理一批节点，更新人物卡片"""
        for node in nodes:
            self._process_node(node)

    def _process_node(self, node: dict):
        """处理单个节点"""
        characters = node.get("characters", [])
        interactions = node.get("interactions", [])
        emotional_arc = node.get("emotional_arc", "")
        importance = node.get("importance", 0.5)
        node_id = node.get("id", "")

        for char in characters:
            name = char.get("name", "")
            state_before = char.get("state_before", "")

            if not name:
                continue

            # 创建或获取卡片
            if name not in self.characters:
                self.characters[name] = CharacterCard(
                    character_id=name,
                    name=name,
                    first_seen=node_id,
                    current_state=state_before
                )

            card = self.characters[name]
            card.increment_appearance()

            # 更新情绪状态
            if emotional_arc and name in emotional_arc:
                # 从 emotional_arc 提取情绪状态，如 "陈屿从'无聊'到'微妙'"
                card.update_emotional_state(state_before, node_id)
            elif state_before:
                card.update_emotional_state(state_before, node_id)

            # 记录关键事件
            if importance >= 0.8:
                card.add_key_event(node_id)

        # 处理 interactions
        for interaction in interactions:
            source_char = self._find_source_char(interactions, interaction)
            if source_char and source_char in self.characters:
                self.characters[source_char].add_interaction(
                    target=interaction.get("target", ""),
                    interaction_type=interaction.get("type", "neutral"),
                    intensity_delta=interaction.get("intensity_delta", 0.0),
                    node_id=node_id
                )

    def _find_source_char(self, interactions: list, target_interaction: dict) -> Optional[str]:
        """从上下文推断interaction的发起者"""
        # 简化：返回第一个角色
        return None

    def get_character(self, name: str) -> Optional[CharacterCard]:
        return self.characters.get(name)

    def get_all_characters(self) -> Dict[str, CharacterCard]:
        return self.characters

    def get_relationship_graph(self) -> dict:
        """输出关系图数据（用于前端）"""
        nodes = []
        edges = []

        for char_name, card in self.characters.items():
            nodes.append({
                "id": char_name,
                "name": char_name,
                "total_appearances": card.total_appearances
            })

            for target, rel in card.relationships.items():
                edges.append({
                    "source": char_name,
                    "target": target,
                    "type": rel.type,
                    "intensity": rel.current_intensity
                })

        return {"nodes": nodes, "edges": edges}

    def get_emotional_timeline(self, character_name: str) -> list:
        """输出角色情绪轨迹（用于前端）"""
        card = self.characters.get(character_name)
        if not card:
            return []
        return [
            {"node_id": e.node_id, "emotion": e.emotion}
            for e in card.emotional_timeline
        ]
```

- [ ] **Step 2: 创建测试**

```python
# tests/core/test_character_tracker.py
import pytest
from src.core.character_tracker import CharacterTracker

def test_create_character_on_first_seen():
    tracker = CharacterTracker()
    nodes = [{
        "id": "n-0-0",
        "characters": [{"name": "陈屿", "state_before": "无聊"}]
    }]
    tracker.process_nodes(nodes)

    assert "陈屿" in tracker.characters
    assert tracker.characters["陈屿"].first_seen == "n-0-0"
    assert tracker.characters["陈屿"].current_state == "无聊"

def test_accumulate_interactions():
    tracker = CharacterTracker()
    nodes = [
        {
            "id": "n-0-0",
            "characters": [{"name": "陈屿", "state_before": "无聊"}],
            "interactions": [{"target": "老板", "type": "tension", "intensity_delta": 0.3}]
        }
    ]
    tracker.process_nodes(nodes)

    assert "老板" in tracker.characters["陈屿"].relationships
    assert tracker.characters["陈屿"].relationships["老板"].current_intensity == 0.3

def test_key_events_for_high_importance():
    tracker = CharacterTracker()
    nodes = [
        {
            "id": "n-0-0",
            "characters": [{"name": "陈屿", "state_before": "无聊"}],
            "importance": 0.85
        }
    ]
    tracker.process_nodes(nodes)

    assert "n-0-0" in tracker.characters["陈屿"].key_events
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/core/test_character_tracker.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/core/character_tracker.py tests/core/test_character_tracker.py
git commit -m "feat(core): add CharacterTracker for character relationship and emotion tracking"
```

---

## Chunk 7: Pipeline 整合

**Files:**
- Modify: `src/core/node_generator.py` - 修改为三阶段调用
- Test: `tests/core/test_node_generator.py` - 更新测试

- [ ] **Step 1: 创建 Pipeline 配置**

```python
# src/core/node_generator.py 新增配置类
class PipelineConfig:
    """流水线配置"""
    enable_agent2_agent3: bool = True  # 绑定开关
    enable_character_tracker: bool = True

    @classmethod
    def from_env(cls):
        return cls(
            enable_agent2_agent3=os.getenv("ENABLE_AGENT2_AGENT3", "true").lower() == "true",
            enable_character_tracker=os.getenv("ENABLE_CHARACTER_TRACKER", "true").lower() == "true"
        )
```

- [ ] **Step 2: 修改 NarrativeNodeGenerator**

```python
# src/core/node_generator.py 修改 generate_from_chunk 方法

class NarrativeNodeGenerator:
    def __init__(self, book_id: str = None, api_key: str = None, model: str = None):
        # ... existing init code ...

    async def generate_from_chunk(self, chunk: Chunk, context: dict = None) -> tuple[list[NarrativeNode], dict]:
        """
        生成节点，返回 (nodes, character_tracker_data)
        """
        context = context or {}
        config = PipelineConfig.from_env()

        # 阶段1: Agent1 - 内容生成
        agent1_nodes = await self._generate_agent1(chunk)

        # 阶段2+3: Agent2 + Agent3（绑定，可选）
        if config.enable_agent2_agent3:
            time_anchors = await self._generate_agent2(agent1_nodes, context.get("last_timeline_state"))
            agent1_nodes = await self._generate_agent3(agent1_nodes, time_anchors)

        # CharacterTracker（可选）
        character_data = {}
        if config.enable_character_tracker:
            tracker = CharacterTracker()
            tracker.process_nodes(agent1_nodes)
            character_data = {
                "characters": tracker.get_all_characters(),
                "relationship_graph": tracker.get_relationship_graph()
            }

        # 转换为 NarrativeNode
        nodes = [self._dict_to_node(n) for n in agent1_nodes]
        return nodes, character_data

    async def _generate_agent1(self, chunk: Chunk) -> list[dict]:
        """Agent1: 内容生成"""
        prompt = BASE_NODE_PROMPT.format(
            text=chunk.text,
            chunk_order=chunk.order,
            last_nodes=""
        )
        # 调用 LLM 获取 nodes
        # ... 复用现有逻辑 ...
        return nodes

    async def _generate_agent2(self, nodes: list, last_timeline_state: dict = None) -> list:
        """Agent2: 时间锚定"""
        resolver = TimeAnchorResolver()
        return await resolver.resolve(nodes, last_timeline_state)

    async def _generate_agent3(self, nodes: list, time_anchors: list) -> list[dict]:
        """Agent3: 结构层"""
        builder = GraphBuilder()
        return await builder.build(nodes, time_anchors)

    def _dict_to_node(self, node_dict: dict) -> NarrativeNode:
        """dict 转 NarrativeNode"""
        characters = [
            CharacterState(name=c.get("name", ""), state_before=c.get("state_before", ""))
            for c in node_dict.get("characters", [])
        ]
        return NarrativeNode(
            id=node_dict["id"],
            parent_chunk_id=node_dict.get("parent_chunk_id", ""),
            beat_index=node_dict.get("beat_index", 0),
            scene=node_dict.get("scene", ""),
            location=node_dict.get("location", ""),
            characters=characters,
            situation=node_dict.get("situation", ""),
            turning_point=node_dict.get("turning_point", ""),
            importance=node_dict.get("importance", 0.5),
            emotional_arc=node_dict.get("emotional_arc", ""),
            interactions=[InteractionModel(**i) for i in node_dict.get("interactions", [])],
            thread_id=node_dict.get("thread_id", "main"),
            timeline_order=node_dict.get("timeline_order", 0),
            # ... 其他字段 ...
        )
```

- [ ] **Step 3: 更新测试**

```python
# tests/core/test_node_generator.py 新增测试
def test_pipeline_with_agent2_agent3_disabled():
    os.environ["ENABLE_AGENT2_AGENT3"] = "false"
    generator = NarrativeNodeGenerator(book_id="test")
    # ... 测试关闭时的行为 ...
    os.environ["ENABLE_AGENT2_AGENT3"] = "true"
```

- [ ] **Step 4: 提交**

```bash
git add src/core/node_generator.py
git commit -m "feat(core): integrate 3-phase pipeline in NarrativeNodeGenerator"
```

---

## 实施完成

**文件变更总结：**
- 新建: `src/models/character_card.py`, `src/core/time_anchor_resolver.py`, `src/core/graph_builder.py`, `src/core/character_tracker.py`
- 新建: `src/prompts/time_anchor.py`, `src/prompts/graph_builder_prompt.py`
- 修改: `src/models/narrative_node.py`, `src/prompts/base_node.py`, `src/core/node_generator.py`
- 新建测试覆盖所有新模块
