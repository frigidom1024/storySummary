"""生成流程相关的数据模型定义（统一入口）"""

# 从 agents.models 导入，保持向后兼容
from src.generation.agents.models import (
    Draft,
    DraftSection,
    ManuscriptOutline,
    OutlineResult,
    StyleProfile,
    ChapterWriterInput,
    ChapterWriterOutput,
    GuideIntroInput,
    GuideIntroOutput,
    GuideReflectionInput,
    GuideReflectionOutput,
    PolishInput,
    PolishOutput,
    ManuscriptResult,
)

__all__ = [
    # 统一草稿模型
    "Draft",
    "DraftSection",
    # Outline
    "ManuscriptOutline",
    "OutlineResult",
    # Style
    "StyleProfile",
    # Writer
    "ChapterWriterInput",
    "ChapterWriterOutput",
    "GuideIntroInput",
    "GuideIntroOutput",
    "GuideReflectionInput",
    "GuideReflectionOutput",
    # Polish
    "PolishInput",
    "PolishOutput",
    # Result
    "ManuscriptResult",
]