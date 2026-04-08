from openai import AsyncOpenAI
from src.core.prompts import DETAIL_RECOVERY_PROMPT


class DetailRecovery:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def enrich(
        self,
        scene: str,
        characters: str,
        event: str,
        excerpt: str
    ) -> str:
        prompt = DETAIL_RECOVERY_PROMPT.format(
            scene=scene,
            characters=characters,
            event=event,
            excerpt=excerpt
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You enrich narrative summaries with vivid sensory details."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()