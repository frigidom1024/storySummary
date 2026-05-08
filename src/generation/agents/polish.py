import os

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
from src.logging_config import debug


class PolishAgent:
    """整合草稿为完整口播稿。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.3)

    async def polish(self, drafts: list[dict], book_info: dict) -> str:
        """整合草稿为完整口播稿

        Args:
            drafts: 按顺序排列的草稿列表，每个草稿包含 section_id, type, content
            book_info: 书籍信息，包含 title, synopsis 等

        Returns:
            完整的口播稿文本
        """
        if not drafts:
            return ""

        # 按 section_id 排序，处理"第X章"格式的章节号
        def get_sort_key(d):
            section_id = d.get("section_id", "")
            if section_id.startswith("第") and "章" in section_id:
                try:
                    return int(section_id.replace("第", "").replace("章", ""))
                except:
                    return 999
            if section_id == "开篇介绍":
                return 0
            if section_id == "思考与总结":
                return 1000
            return 500

        sorted_drafts = sorted(drafts, key=get_sort_key)

        # 构建草稿列表文本，保留类型信息
        drafts_text = "\n\n".join(
            f"【{d.get('section_id', f'章节{i}')}】（{d.get('type', 'content')}）\n{d.get('content', '')}"
            for i, d in enumerate(sorted_drafts, 1)
        )

        system_prompt = """你是资深口播稿编辑，擅长将多个章节草稿整合成一篇完整、流畅、有吸引力的口播稿。

## 整合要求（严格遵守）
1. 【强制】保持每个草稿的核心内容完整，不遗漏重要细节，不新增剧情或事实
2. 【强制】添加自然的章节衔接语句，使全文流畅连贯
3. 统一全文语气为口语化、亲切、自然，像朋友聊天一样
4. 去除重复表达，但保留必要的细节
5. 开头要有吸引人的引入，结尾要有深刻的收束（不要用"下期再见"等程式化收尾语）
6. 保持故事的叙事节奏，适当加入过渡句让听众有时间消化
7. 对于"开篇介绍"类型，保持介绍性内容，自然引出故事
8. 对于"story_content"类型，保持故事叙述的连贯性和细节
9. 对于"思考与总结"类型，深入分析主题，引发听众思考

## 输出要求
直接输出一篇完整的口播稿正文，不要加标题，不要加说明，不要分段输出注释。
"""

        user_prompt = f"""请将以下草稿整合成一篇完整的口播稿。

书籍信息：
- 书名：{book_info.get('title', '未知')}
- 故事梗概：{book_info.get('synopsis', '无')}

草稿内容：
{drafts_text}

请直接输出一篇完整的口播稿。"""

        if self.debug_mode:
            debug("polish", "[POLISH] drafts_count={}, total_length={}", len(drafts), sum(len(d.get('content', '')) for d in drafts))

        response = await self.llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        if not response.content:
            return "\n\n".join(d.get('content', '') for d in sorted_drafts)
        return response.content.strip()