"""节点生成相关提示词"""

# ====================== 多节点生成提示词 ======================
MULTI_BEAT_NODE_PROMPT = """你是一个专业的小说场记师。你的任务不是总结情节，而是为每个叙事原子创建索引卡。

## 什么是叙事原子（Beat）

叙事原子是故事的最小单元：
- 同一场景（时间+地点不变）
- 同一组人物在场
- 一个完整的情感转折或事件推进

## 节点创建规则

1. 同一地点 + 连续时间 + 相关事件 → 一个节点
2. 任何地点变化 → 新节点（同一建筑不同房间也算）
3. 时间跳跃（即使同一天：下午→傍晚）→ 新节点
4. 任何显著的情感转折 → 应该是独立的节点
5. 不要为了保持节点简短而合并不同的情感转折

## 输出格式

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

### 示例

**单线倒叙（timeline_order）：**
```json
{{
  "id": "n-0-0",
  "timeline_order": 0,
  "timeline_anchor": "现在",
  "is_time_jump": true,
  "jump_direction": "past",
  "jump_label": "倒叙",
  "thread_id": "main",
  "thread_prev_node_id": ""
}}
```

**多线叙事（thread_id）：**
```json
{{
  "id": "n-0-0",
  "thread_id": "zhang",
  "thread_name": "张医生线",
  "thread_prev_node_id": ""
}}
```

**汇聚点：**
```json
{{
  "id": "n-0-6",
  "is_convergence": true,
  "characters": [{{"name": "张医生"}}, {{"name": "陈薇"}}, {{"name": "老周"}}]
}}
```

每个chunk输出一个JSON数组，每个对象包含：

```json
[
  {{
    "id": "n-{chunk_order}-{{beat_index}}",
    "parent_chunk_id": "chunk-{{chunk_order}}",
    "beat_index": 0,
    "scene": "Time & Location (e.g., '青岛路旧书店，下午三点多')",
    "location": "简化为地点 (e.g., '青岛路旧书店')",
    "scene_timing": "时间段 (e.g., '午后')",
    "characters": [
      {{
        "name": "Character name",
        "state_before": "进入这个场景时的情绪/状态"
      }}
    ],
    "situation": "此刻[角色]面临[情境/问题]，一句话不超过25字",
    "turning_point": "[角色]的[行为/决定/反应]改变了[什么]，或'渐变：...'",
    "emotional_arc": "[角色A]从[X]到[Y] / [角色B]从[X]到[Y]",
    "mood_tone": "氛围关键词，3个，用逗号分隔",
    "narrative_rhythm": "slow / steady / fast / pause 选一",
    "discussion_prompts": [
      "2-3个问题，站在'这个情节为什么重要'的角度",
      "避免问'发生了什么'，要问'这意味着什么'"
    ],
    "relationship_delta": [
      {{"pair": "A-B", "from": "X", "to": "Y"}}
    ],
    "narrative_role": "opening / rising / climax / ending",
    "timeline_order": 0,
    // 新: 本chunk内相对顺序: 0=现在, -1=过去一步, +1=未来一步
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
  }}
]
```

## 关键原则

- situation：描述"什么在发生"，不是"发生了什么"
- turning_point：标注核心变化，如果是渐进式写"渐变：..."
- emotional_arc：每个在场角色都要记录情绪变化
- relationship_delta：每对同时在场且发生互动的角色都要记录
- mood_tone：用感官/情绪词汇，不用动作词汇

## 示例

❌ 错误（总结模式）：
"situation": "陈屿走进书店，坐下来看书，他看到扉页有签名"

✓ 正确（索引模式）：
"situation": "陈屿需要一个不被打扰的地方消磨时间"
"turning_point": "他在旧书堆里发现一本扉页有签名的《围城》，产生了微妙的占有欲"
"emotional_arc": "陈屿从'无所谓'到'想要拥有'"
"mood_tone": "慵懒, 偶然, 微妙"

Text to analyze:
{text}"""

# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("multi_beat_node", MULTI_BEAT_NODE_PROMPT)
