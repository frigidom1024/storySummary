"""写作相关提示词"""

from string import Template
from typing import Optional

# ====================== 预设风格 ======================
STYLE_TEMPLATES = {
    "轻松聊天": {
        "name": "轻松聊天",
        "description": "口语化、随意、像朋友聊天",
        "style_rules": """
- 大量使用口头禅（"是吧"、"怎么说呢"、"你像"、"说实话"）
- 语气轻松，偶尔调侃
- 可以用网络用语但不要太过
- 结尾可以用"今天的聊一聊就到这儿"之类""",
    },
    "深度解读": {
        "name": "深度解读",
        "description": "有深度、偏分析、注重含义",
        "style_rules": """
- 分析情节背后的含义和象征
- 联系社会现实或人生哲理
- 语气沉稳、思考性
- 个人感悟比复述情节更重要""",
    },
    "故事讲述": {
        "name": "故事讲述",
        "description": "注重叙事、悬念感、吸引听众",
        "style_rules": """
- 像讲故事一样有节奏感
- 善用悬念和转折
- 适当留白让听众思考
- 语气随情节变化有起伏""",
    },
    "专业评论": {
        "name": "专业评论",
        "description": "评论式、点评人物和情节",
        "style_rules": """
- 对人物行为有点评和分析
- 评价情节设计的巧妙之处
- 可以对比其他作品
- 语气像资深编辑或评论家""",
    },
}

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
${style_section}
## 本章叙事节点（播客讲述骨架）
${nodes_summary}

## 本章完整原文（参考素材，不要大段朗读）
```原文
${chunk_text}
```
${reference_section}""")

# ====================== 参考口播稿模板 ======================
REFERENCE_SCRIPT_TEMPLATE = Template("""
## 参考口播稿（学习此风格）
```参考
${reference_script}
```""")


def build_style_system_prompt(
    style_key: Optional[str] = None,
    custom_rules: Optional[str] = None,
) -> str:
    """构建带风格的系统提示词"""
    base = CHAPTER_WRITING_SYSTEM
    if not style_key and not custom_rules:
        return base

    additions = ["\n\n## 风格要求"]
    if style_key and style_key in STYLE_TEMPLATES:
        style = STYLE_TEMPLATES[style_key]
        additions.append(f"\n【{style['name']}】{style['style_rules']}")
    if custom_rules:
        additions.append(f"\n【自定义要求】\n{custom_rules}")

    return base + "\n".join(additions)


def build_writing_prompt(
    chapter_title: str,
    chapter_summary: str,
    core_themes: str,
    established_claims: str,
    nodes_summary: str,
    chunk_text: str,
    style_key: Optional[str] = None,
    custom_rules: Optional[str] = None,
    reference_script: Optional[str] = None,
) -> dict:
    """构建写作提示词的完整消息"""
    # 构建风格说明
    style_section = ""
    if style_key or custom_rules:
        style_parts = []
        if style_key and style_key in STYLE_TEMPLATES:
            style_parts.append(f"【风格：{STYLE_TEMPLATES[style_key]['name']}】{STYLE_TEMPLATES[style_key]['description']}")
        if custom_rules:
            style_parts.append(f"【自定义要求】{custom_rules}")
        style_section = "\n".join(style_parts)

    # 构建参考稿说明
    reference_section = ""
    if reference_script:
        reference_section = REFERENCE_SCRIPT_TEMPLATE.substitute(reference_script=reference_script)

    user_content = CHAPTER_WRITING_USER_TEMPLATE.substitute(
        chapter_title=chapter_title,
        chapter_summary=chapter_summary,
        core_themes=core_themes,
        established_claims=established_claims,
        nodes_summary=nodes_summary,
        chunk_text=chunk_text,
        style_section=style_section,
        reference_section=reference_section,
    )

    return {
        "system": build_style_system_prompt(style_key, custom_rules),
        "user": user_content,
    }


# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("writing_system", CHAPTER_WRITING_SYSTEM)
global_registry.register("writing_user_template", str(CHAPTER_WRITING_USER_TEMPLATE.template))
