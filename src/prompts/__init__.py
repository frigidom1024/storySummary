"""Prompt 系统 - 模块化提示词管理"""

# 导入子模块以触发注册
from . import writing
from . import polish
from . import node
from . import detail
from . import planning

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
]
