"""向后兼容导出 - 所有提示词已迁移到 src/prompts/"""
from src.prompts import (
    CHAPTER_WRITING_SYSTEM,
    CHAPTER_WRITING_USER_TEMPLATE,
    build_writing_prompt,
    POLISH_SYSTEM,
    POLISH_USER_TEMPLATE,
    build_polish_user_input,
    MULTI_BEAT_NODE_PROMPT,
    DETAIL_RECOVERY_PROMPT,
    PODCAST_GENERATION_PROMPT,
    PLANNING_PROMPT,
)

__all__ = [
    "CHAPTER_WRITING_SYSTEM",
    "CHAPTER_WRITING_USER_TEMPLATE",
    "build_writing_prompt",
    "POLISH_SYSTEM",
    "POLISH_USER_TEMPLATE",
    "build_polish_user_input",
    "MULTI_BEAT_NODE_PROMPT",
    "DETAIL_RECOVERY_PROMPT",
    "PODCAST_GENERATION_PROMPT",
    "PLANNING_PROMPT",
]
