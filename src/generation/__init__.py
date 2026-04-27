"""精简版口播稿生成包。"""

from .models import ChapterDraft, ManuscriptResult
from .state import WritingPhase, WritingState
from .agents.outline import OutlineAgent
from .research_tools import ManuscriptResearchToolkit
from .agents.style import StyleLearningAgent
from .writer import ChapterWriter
from .polish import PolishAgent
from .pipeline import ManuscriptPipeline

__all__ = [
    "ChapterDraft",
    "ManuscriptResult",
    "WritingPhase",
    "WritingState",
    "OutlineAgent",
    "ManuscriptResearchToolkit",
    "StyleLearningAgent",
    "ChapterWriter",
    "PolishAgent",
    "ManuscriptPipeline",
]
