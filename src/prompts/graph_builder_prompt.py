GRAPH_BUILDER_PROMPT = """你是叙事结构分析师。请基于角色重叠度给出 thread 建议。

输入：
- nodes
- recent_nodes
- thread_summaries

输出 JSON 数组，每项字段：
- node_id
- thread_hint: main | new | uncertain
- link_confidence: 0.0-1.0

要求：
- 只输出 JSON 数组
- 依据角色重叠判断，重叠高优先 main

Current nodes:
{nodes}

Recent nodes:
{recent_nodes}

Thread summaries:
{thread_summaries}
"""

from .registry import global_registry

global_registry.register("graph_builder", GRAPH_BUILDER_PROMPT)
