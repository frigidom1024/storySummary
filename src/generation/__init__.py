"""精简版口播稿生成包。"""

from .models import (
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
from .state import PipelinePhase, WritingPhase, WritingState
from .agents.outline import OutlineAgent
from .research_tools import ManuscriptResearchToolkit
from .agents.style import StyleLearningAgent
from .agents.writer import ChapterWriter
from .agents.guide import GuideAgent
from .agents.polish import PolishAgent
from .pipeline import ManuscriptPipeline

__all__ = [
    # Models
    "Draft",
    "DraftSection",
    "ManuscriptOutline",
    "OutlineResult",
    "StyleProfile",
    "ChapterWriterInput",
    "ChapterWriterOutput",
    "GuideIntroInput",
    "GuideIntroOutput",
    "GuideReflectionInput",
    "GuideReflectionOutput",
    "PolishInput",
    "PolishOutput",
    "ManuscriptResult",
    # State
    "PipelinePhase",
    "WritingPhase",
    "WritingState",
    # Agents
    "OutlineAgent",
    "ManuscriptResearchToolkit",
    "StyleLearningAgent",
    "ChapterWriter",
    "GuideAgent",
    "PolishAgent",
    "ManuscriptPipeline",
]
