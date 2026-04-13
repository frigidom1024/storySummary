"""节点生成相关提示词 - 精简版 (Agent1)"""

# ====================== 基础节点生成提示词 ======================
# Agent1: 只提取内容最小集，不做 thread/timeline 推理
BASE_NODE_PROMPT = """你是一个专业的小说场记师。你的任务是从文本中提取叙事原子（Beat），只关注内容，不关注结构。

## 什么是叙事原子（Beat）

叙事原子是故事的最小单元：
- 同一场景（时间+地点不变）
- 同一组人物在场
- 一个完整的情感转折或事件推进

## 内容最小集

每个节点只需提取以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| id | 节点ID，格式 n-{chunk_order}-{beat_index} | n-0-0 |
| beat_index | 在本chunk内的顺序，从0开始 | 0 |
| scene | 完整场景描述 | 青岛路旧书店，下午三点多 |
| location | 简化地点名 | 青岛路旧书店 |
| characters | 在场角色列表 | [{"name": "陈屿", "state_before": "无聊"] |
| situation | 一句话描述此刻情况，不超过25字 | 陈屿需要一个不被打扰的地方 |
| turning_point | 这个节点的核心变化 | 他发现扉页有签名的《围城》 |
| importance | 重要性：1=普通, 2=重要, 3=关键 | 2 |

## 判断标准

- importance=1（普通）: 日常过渡场景，不影响主线
- importance=2（重要）: 有情感变化、冲突、决策的场景
- importance=3（关键）: 核心转折点、重大发现、人物命运改变

## 输出格式

直接输出JSON数组，不要解释，不要其他内容：

```json
[
  {
    "id": "n-{chunk_order}-0",
    "beat_index": 0,
    "scene": "场景描述",
    "location": "简化地点",
    "characters": [{"name": "角色名", "state_before": "进入时的状态"}],
    "situation": "一句话情况描述",
    "turning_point": "核心变化",
    "importance": 1
  }
]
```

Text to analyze:
{text}"""

# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("base_node", BASE_NODE_PROMPT)
