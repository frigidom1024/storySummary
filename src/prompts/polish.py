"""润色相关提示词"""

# ====================== 系统提示词 ======================
POLISH_SYSTEM = """你是一个专业播客稿编辑，负责对多章节小说解说稿进行逐章高质量润色。

润色规则：
1. 消除重复内容
2. 统一口语化语气
3. 强化章节过渡自然
4. 结尾升华主题
5. 加入主播个人思考，不要纯复述
6. 必须对照原文核实情节

你可以使用工具查看任意章节原文，确保润色准确。
请一步一步思考，先规划，再调用工具，最后输出完整润色稿。

输出格式必须严格遵守：
【第X章润色】
内容

【完整稿子】
全部合并内容
"""

# ====================== 用户输入模板 ======================
POLISH_USER_TEMPLATE = """请润色以下多章节播客稿：

## 章节索引
{index}

## 待润色稿子
{drafts}

请先通读全文 → 按需调用get_chunk_context核对原文 → 逐章润色 → 输出最终稿。"""


def build_polish_user_input(index: str, drafts: str) -> str:
    """构建润色用户输入"""
    return POLISH_USER_TEMPLATE.format(index=index, drafts=drafts)


# ====================== 注册到全局注册表 ======================
from .registry import global_registry

global_registry.register("polish_system", POLISH_SYSTEM)
global_registry.register("polish_user_template", POLISH_USER_TEMPLATE)
