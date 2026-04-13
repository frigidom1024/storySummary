TIME_ANCHOR_PROMPT = """你是一个时间分析师。请为每个节点判断时间位置。

输入包含：
- last_timeline_state: 上一个 chunk 的时间状态
- nodes: 当前节点数组（每项至少有 id/scene）

输出 JSON 数组，每项字段：
- node_id
- time_type: present | past | future
- relative_to_prev: continue | jump | unclear
- anchor_hint
- confidence (0.0-1.0)

要求：
- 只输出 JSON 数组，不要解释
- 判断不确定时，relative_to_prev 用 unclear 且 confidence <= 0.6

Context from previous chunk:
{last_timeline_state}

Nodes to analyze:
{nodes}
"""

from .registry import global_registry

global_registry.register("time_anchor", TIME_ANCHOR_PROMPT)
