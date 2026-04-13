"""Prompt 系统 - 模块化提示词管理"""

# 导入子模块以触发注册
from . import writing
from . import polish
from . import node
from . import detail
from . import planning
from . import time_anchor
from . import graph_builder_prompt

# 从 registry 导出
from .registry import (
    PromptRegistry,
    global_registry,
    get_prompt,
    register_prompt,
    register_builder,
)

# 导出提示词常量
from .writing import (
    CHAPTER_WRITING_SYSTEM,
    CHAPTER_WRITING_USER_TEMPLATE,
    build_writing_prompt,
    build_style_system_prompt,
    STYLE_TEMPLATES,
)

from .polish import (
    POLISH_SYSTEM,
    POLISH_USER_TEMPLATE,
    build_polish_user_input,
)

from .node import MULTI_BEAT_NODE_PROMPT

from .detail import (
    DETAIL_RECOVERY_PROMPT,
    PODCAST_GENERATION_PROMPT,
)

from .planning import PLANNING_PROMPT
from .time_anchor import TIME_ANCHOR_PROMPT
from .graph_builder_prompt import GRAPH_BUILDER_PROMPT

__all__ = [
    # Registry
    "PromptRegistry",
    "global_registry",
    "get_prompt",
    "register_prompt",
    "register_builder",
    # Writing
    "CHAPTER_WRITING_SYSTEM",
    "CHAPTER_WRITING_USER_TEMPLATE",
    "build_writing_prompt",
    "build_style_system_prompt",
    "STYLE_TEMPLATES",
    # Polish
    "POLISH_SYSTEM",
    "POLISH_USER_TEMPLATE",
    "build_polish_user_input",
    # Node
    "MULTI_BEAT_NODE_PROMPT",
    # Detail
    "DETAIL_RECOVERY_PROMPT",
    "PODCAST_GENERATION_PROMPT",
    # Planning
    "PLANNING_PROMPT",
    # Agent2 / Agent3
    "TIME_ANCHOR_PROMPT",
    "GRAPH_BUILDER_PROMPT",
]
