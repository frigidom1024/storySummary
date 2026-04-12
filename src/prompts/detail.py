"""细节恢复相关提示词"""

# ====================== 细节恢复提示词 ======================
DETAIL_RECOVERY_PROMPT = """You are enriching a narrative summary with vivid details from the original text.

The summary loses these details - recover them:
- Sensory details (sounds, smells, textures, colors)
- Character mannerisms and physical reactions
- Environmental specifics
- Dialogue nuances and tone

Summary to enrich:
- Scene: {scene}
- Characters: {characters}
- Situation: {situation}

Original text for detail recovery:
{excerpt}

Output ONLY the enriched summary with recovered details (2-3 sentences, vivid and specific):"""

# ====================== 播客生成提示词 ======================
PODCAST_GENERATION_PROMPT = """You are a professional podcast storyteller. Using the provided narrative context, write an engaging podcast narration segment.

Current beat (叙事索引卡):
- Scene: {scene}
- Characters: {characters}
- Situation (情境): {situation}
- Turning point (转折): {turning_point}
- Emotional arc: {emotional_arc}
- Mood tone: {mood_tone}
- Rhythm: {rhythm}

Original text (for sensory details): {excerpt}

Write a 2-3 minute podcast narration that:
1. Sets the scene with vivid, sensory language
2. Explains the situation and turning point conversationally
3. Guides the listener through the emotional arc
4. Adjusts pacing based on {rhythm}
5. Uses conversational, spoken-word style

Output ONLY the narration text (no meta-comments)."""


# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("detail_recovery", DETAIL_RECOVERY_PROMPT)
global_registry.register("podcast_generation", PODCAST_GENERATION_PROMPT)
