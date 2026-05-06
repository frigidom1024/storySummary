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
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.4)

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

        # 按 section_id 排序
        sorted_drafts = sorted(drafts, key=lambda d: d.get("section_id", ""))

        # 构建草稿列表文本
        drafts_text = "\n\n".join(
            f"【{d.get('section_id', f'章节{i}')}】\n{d.get('content', '')}"
            for i, d in enumerate(sorted_drafts, 1)
        )

        system_prompt = """你是口播稿编辑，负责将多个草稿整合成一篇完整、流畅的口播稿。

## 整合要求
1. 保持每个草稿的核心内容不变，不新增剧情或事实
2. 添加章节之间的衔接语句，使全文流畅自然
3. 统一全文语气、风格、口吻
4. 去除重复表达
5. 保持口语化表达，像朋友聊天一样自然
6. 开头要有引入，结尾要有自然的收束（但不要用"下期再见"等收尾语）

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