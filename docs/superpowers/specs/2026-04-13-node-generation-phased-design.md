# 分阶段节点生成设计

## 背景

当前 `node_generator.py` 在一次 LLM 调用中生成整个 chunk 的所有 beats（约 25 个字段）。这导致：
- 单次输出信息密度过高，AI 容易出现幻觉
- 结构字段（timeline、thread）和内容字段混淆
- 无法针对性优化不同类型的字段质量

## 设计目标

将节点生成拆分为三个阶段，每阶段职责单一，降低单次 LLM 调用复杂度。

---

## 架构总览

```
chunk[N] → Agent1 → nodes (content)
                ↓
         Agent2 → time_type + anchor_hint
                ↓
         Agent3 → thread_id + prev_node_id
                ↓
         程序 merge → 完整节点
```

---

## 阶段详细设计

### 🥇 Agent1：语义层（内容生成）

**输入：** 原始 chunk 文本 + 上一个 chunk 的摘要（last_nodes）

**输出：**
```json
{
  "nodes": [
    {
      "id": "n-{chunk_order}-{beat_index}",
      "beat_index": 0,
      "scene": "青岛路旧书店，下午三点多",
      "location": "青岛路旧书店",
      "scene_timing": "午后",
      "characters": [
        {"name": "陈屿", "state_before": "无聊"}
      ],
      "situation": "陈屿需要一个不被打扰的地方",
      "turning_point": "他发现扉页有签名的《围城》",
      "emotional_arc": "陈屿从'无所谓'到'想要拥有'",
      "mood_tone": "慵懒, 偶然, 微妙",
      "narrative_rhythm": "steady",
      "importance": 2,
      "interactions": [
        {
          "pair": "陈屿-老板",
          "type": "tension",
          "change": "low→medium"
        }
      ]
    }
  ]
}
```

**职责：**
- 节点切分（判断 scene 边界）
- 基础语义提取（situation、turning_point）
- 情绪弧线识别（emotional_arc）
- 交互感知（interactions，非 relationship_delta）

**不负责：**
- timeline 判断
- thread 连接
- 节点间的结构关系

**Prompt 设计要点：**
- 只输出内容字段，不输出 timeline/thread 相关字段
- interactions 描述"感知到的关系变化"，不要求结构化图

---

### 🥈 Agent2：时间层（时间锚定）

**输入：** Agent1 输出的 nodes + 上一个 chunk 的 timeline 状态

**输出：**
```json
{
  "node_id": "n-1-2",
  "time_type": "past | present | future",
  "relative_to_prev": "continue | jump | unclear",
  "anchor_hint": "大学时期",
  "confidence": 0.8
}
```

**职责：**
- 判断每个节点是"过去/现在/未来"
- 判断与前一个节点的时间关系（延续/跳跃/不确定）
- 提供时间锚点提示（timeline_anchor）

**不负责：**
- thread 连接
- 节点间的结构关系

**Prompt 设计要点：**
- 每次处理一个节点（不是批量）
- 需要看到前一个节点的时间状态作为参考
- `relative_to_prev` 判断标准：
  - `continue`：时间自然推进（如下午→傍晚，同一地点）
  - `jump`：时间跳跃（回忆、插叙、时间线切换）
  - `unclear`：无法判断

**时间判断算法（参考）：**
```
if relative_to_prev == "continue":
    timeline_order 保持不变
elif time_type == "past":
    timeline_order -= 1
elif time_type == "future":
    timeline_order += 1
```

---

### 🥉 Agent3：结构层（混合架构）

**输入：** Agent1 + Agent2 的输出 + 全局 nodes_so_far

**输出：**
```json
{
  "node_id": "n-1-2",
  "thread_hint": "main | new | uncertain",
  "link_confidence": 0.6
}
```

**职责：**
- 提供 thread 方向的 hint（LLM 部分）
- 程序负责实际的 thread 分配和 prev_node 连接

**LLM 职责（轻量）：**
- 基于角色重叠度判断是否延续当前 thread
- 输出 `thread_hint`（main/new/uncertain）

**程序职责（核心）：**
```python
# 1. timeline_order 计算
if relative_to_prev == "continue":
    keep previous value
elif time_type == "past":
    decrement
elif time_type == "future":
    increment

# 2. thread 分配
if thread_hint == "new" or no character overlap:
    assign new thread_id
else:
    continue same thread

# 3. prev_node 查找
prev_node = find_last_node_in_thread(thread_id, all_nodes_so_far)
```

**为什么不把 thread 完全交给 LLM：**
- 幻觉风险高（容易断链、串线）
- 程序规则更稳定（基于角色重叠度判断）
- LLM 只提供"方向性建议"，执行由程序完成

---

## 滑动上下文设计

每个 chunk 处理时，需要携带"上下文摘要"：

| 阶段 | 上下文内容 |
|------|-----------|
| Agent1 | `last_nodes`（上一个 chunk 的节点列表，只含 scene + characters） |
| Agent2 | `last_timeline_state`（上一个 chunk 的 timeline_order 范围） |
| Agent3 | `all_nodes_so_far`（所有历史节点，用于 thread 查找） |

**注意：** 上下文要精简，避免污染当前 chunk 的判断。

---

## 实施计划

### 第一步：Agent1（已有基础）
- 复用 `base_node.py` 的 `BASE_NODE_PROMPT`
- 扩展输出包含 `interactions` 字段
- 添加 `last_nodes` 上下文输入

### 第二步：Agent2（新增）
- 新建 `TimeAnchorResolver` 类
- 设计 prompt，关注 `time_type` 和 `relative_to_prev`
- 处理单节点时间判断

### 第三步：Agent3（混合）
- 新建 `GraphBuilder` 类
- LLM 部分：轻量 thread_hint
- 程序部分：thread 分配、prev_node 连接、timeline_order 计算

### 第四步：流水线整合
- 修改 `NarrativeNodeGenerator` 支持三阶段调用
- 实现滑动上下文传递
- 程序 merge 更新逻辑

---

## 关键原则

1. **谁产生语义，谁负责内容** — Agent1 负责内容，不做结构
2. **谁维护结构，谁负责关系** — Agent3 + 程序负责 graph，不让 Agent1 猜关系
3. **LLM 只给 hint，程序做执行** — 稳定性优于灵活性
4. **单阶段职责单一** — 每阶段只做一个类型的判断，不混淆
