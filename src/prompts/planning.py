"""规划相关提示词"""

# ====================== 章节规划提示词 ======================
PLANNING_PROMPT = """你是一个资深播客策划师。你的任务是从一部小说的叙事节点索引中提取结构信息，用于规划播客节目的章节划分。

## 叙事节点索引说明
每个叙事节点包含：
- scene: 场景（时间+地点）
- situation: 核心情境（1句话）
- turning_point: 转折点
- emotional_arc: 情绪弧
- narrative_role: 叙事角色（opening/rising/climax/ending）
- characters: 在场角色列表

## 你的任务

分析全部叙事节点后，输出一个 JSON 结构：

```json
{{
  "chapters": [
    {{
      "chunk_id": "chunk-0001",
      "title": "章节标题（简洁，10字以内）",
      "summary": "这个章节要讲什么（1-2句话）"
    }}
  ],
  "overall_tone": "播客整体基调描述（3-5句话）",
  "core_themes": ["核心主题1", "核心主题2", "核心主题3"]
}}
```

## 注意事项

- chapters 数量不代表叙事节点数量，而是播客"章"的数量
- 相邻的同类叙事节点可以合并为一章
- overall_tone 要体现播客风格（如"带有敬畏感的理性探讨"）
- core_themes 是贯穿全书的核心观点，后面章节要呼应

## 叙事节点列表：
{nodes_summary}
"""


# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("planning", PLANNING_PROMPT)
