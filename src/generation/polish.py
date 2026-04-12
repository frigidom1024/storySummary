import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.prompts import POLISH_PROMPT
from src.core.node_generator import create_llm


class PolishPass:
    """润色器"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.llm = create_llm(api_key=self.api_key, model=model, temperature=0.7)

    async def polish(self, draft: str) -> str:
        """润色完整草稿"""
        prompt = POLISH_PROMPT.format(full_manuscript=draft)

        messages = [
            SystemMessage(content="你是一个播客稿编辑，输出纯文本。"),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        if not response.content:
            raise ValueError("LLM returned empty response")

        return response.content.strip()
