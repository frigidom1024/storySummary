import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.prompts import DETAIL_RECOVERY_PROMPT
from src.core.node_generator import create_llm


class DetailRecovery:
    def __init__(self, api_key: str = None, model: str = None):
        self.llm = create_llm(api_key=api_key, model=model, temperature=0.6, max_tokens=300)

    async def enrich(
        self,
        scene: str,
        characters: str,
        situation: str,
        excerpt: str
    ) -> str:
        prompt = DETAIL_RECOVERY_PROMPT.format(
            scene=scene,
            characters=characters,
            situation=situation,
            excerpt=excerpt
        )

        messages = [
            SystemMessage(content="You enrich narrative summaries with vivid sensory details."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()
