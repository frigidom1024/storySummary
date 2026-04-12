"""写作相关提示词"""

from string import Template

# ====================== 系统提示词 ======================
CHAPTER_WRITING_SYSTEM = """你是一个播客主播，正在录制一期"聊一聊"风格的节目。

## 写作风格要求
- 口语化，像在跟朋友聊天
- 先聊情节（用 NarrativeNode 索引作为骨架），再穿插个人思考
- 可以从原文提取生动细节作为"聊"的素材，但不要大段朗读原文
- 适当使用口头禅（如"是吧"、"怎么说呢"、"你像"）
- 每个章节要有自然的过渡句，承接上文引出下文

## 输出格式
直接输出一章的播客稿，不要前缀说明，不要章节标题（已在基本信息中给出），直接开始聊。
"""

# ====================== 用户输入模板 ======================
CHAPTER_WRITING_USER_TEMPLATE = Template("""## 本章基本信息
- 章节标题：${chapter_title}
- 章节摘要：${chapter_summary}
- 全书核心主题：${core_themes}
- 上文已确立的观点（不要重复，要承接）：${established_claims}

## 本章叙事节点（播客讲述骨架）
${nodes_summary}

## 本章完整原文（参考素材，不要大段朗读）
```原文
${chunk_text}
```""")


def build_writing_prompt(
    chapter_title: str,
    chapter_summary: str,
    core_themes: str,
    established_claims: str,
    nodes_summary: str,
    chunk_text: str,
) -> dict:
    """构建写作提示词的完整消息"""
    user_content = CHAPTER_WRITING_USER_TEMPLATE.substitute(
        chapter_title=chapter_title,
        chapter_summary=chapter_summary,
        core_themes=core_themes,
        established_claims=established_claims,
        nodes_summary=nodes_summary,
        chunk_text=chunk_text,
    )
    return {
        "system": CHAPTER_WRITING_SYSTEM,
        "user": user_content,
    }


# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("writing_system", CHAPTER_WRITING_SYSTEM)
global_registry.register("writing_user_template", CHAPTER_WRITING_USER_TEMPLATE.template if hasattr(CHAPTER_WRITING_USER_TEMPLATE, 'template') else str(CHAPTER_WRITING_USER_TEMPLATE))
