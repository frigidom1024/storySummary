TIME_ANCHOR_PROMPT = """你是一个时间分析师。请为每个节点判断时间位置。

输入包含：
- last_timeline_state: 上一个 chunk 的时间状态
- nodes: 当前节点数组（每项至少有 id/scene）

输出 JSON 数组，每项字段：
- node_id
- time_type: present | past | future
- relative_to_prev: continue | jump | unclear
- anchor_hint: 简短的时间锚点描述
- confidence (0.0-1.0)

## time_type 判断规则

- **present**: 当前故事主线时间，场景描述如"现在"、"此刻"、"今天"、"午后"
- **past**: 回忆、梦境、过去的时间跳转。关键词：一周后、回忆、梦里、曾经、那年、深夜、那时、过去、小时后、分钟过去
- **future**: 预想、计划、展望未来（较少用）

## relative_to_prev 判断规则

- **continue**: 场景或时间与上一个节点紧密连接，没有明显跳转
- **jump**: 场景发生明显变化，包括：
  - 时间跨度变化（一周后、几天后、深夜）
  - 地点重大变化
  - 回忆/梦境片段
- **unclear**: 无法判断时使用

## 时间标记词示例

past 时间词：一周后、回忆、梦里、曾经、那年、深夜、那时、过去、小时后、分钟过去
present 时间词：现在、此刻、今天、午后、当前、与此同时
future 时间词：将来、以后、某天、多年后

要求：
- 只输出 JSON 数组，不要解释
- 如果 scene 或 anchor_hint 中包含 past 时间词，优先判断为 past

Context from previous chunk:
{last_timeline_state}

Nodes to analyze:
{nodes}"""

from .registry import global_registry

global_registry.register("time_anchor", TIME_ANCHOR_PROMPT)
