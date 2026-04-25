import os

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.node_generator import create_llm
from src.logging_config import debug
from src.models.chunk import Chunk


class PolishAgent:
    """全文润色（可选一步）。"""

    def __init__(self, api_key: str = None, model: str = None, debug_mode: bool = False):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.debug_mode = debug_mode
        self.llm = create_llm(api_key=self.api_key, model=self.model, temperature=0.4)

    async def polish(self, draft_text: str, chunks: list[Chunk]) -> str:
        if not draft_text.strip():
            return draft_text

        chapter_count = len(chunks)
        system_prompt = """你是口播稿编辑。
- 保持原有事实不变，不新增剧情。
- 统一语气，减少重复表达，增强章节衔接。
- 保持口语化，不要变成书面论文。"""
        user_prompt = f"""这是一本书的完整口播草稿（共 {chapter_count} 章），请做轻量润色：

```草稿
{draft_text}
```

请直接输出润色后的全文。"""

        if self.debug_mode:
            debug("polish", "[POLISH] input_length={}", len(draft_text))

        response = await self.llm.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        if not response.content:
            return draft_text
        return response.content.strip()
