import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.narrative_node import NarrativeNode
from src.storage.vector_store import VectorStore
from src.core.prompts import PODCAST_GENERATION_PROMPT
from src.core.detail_recovery import DetailRecovery
from src.core.node_generator import create_llm


class PodcastGenerator:
    def __init__(self, api_key: str = None, vector_store: VectorStore = None, model: str = None):
        self.llm = create_llm(api_key=api_key, model=model, temperature=0.8, max_tokens=800)
        self.vector_store = vector_store
        self.detail_recovery = DetailRecovery(api_key=api_key, model=model)

    def _format_characters(self, node: NarrativeNode) -> str:
        return ", ".join([
            f"{c.name} ({c.state}, goal: {c.goal})" for c in node.characters
        ])

    async def generate_segment(
        self,
        node: NarrativeNode,
        original_excerpt: str,
        prev_node: NarrativeNode = None,
        context_nodes: list[NarrativeNode] = None
    ) -> str:
        # Step 1: Recover details from original text
        enriched_scene = await self.detail_recovery.enrich(
            scene=node.scene,
            characters=self._format_characters(node),
            event=node.event,
            excerpt=original_excerpt
        )

        # Step 2: Get state delta for character evolution
        state_delta = node.state_delta if hasattr(node, 'state_delta') else ""

        # Step 3: Build context from previous nodes
        context = ""
        if prev_node:
            context = f"Previous beat: {prev_node.scene}. What happened: {prev_node.event}\n"
        if context_nodes:
            context += "Earlier context:\n" + "\n".join([
                f"- {n.scene}: {n.event}" for n in context_nodes[-2:]
            ])

        # Step 4: Generate podcast with all context
        prompt = PODCAST_GENERATION_PROMPT.format(
            scene=enriched_scene,
            characters=self._format_characters(node),
            event=node.event,
            tension=node.tension,
            stakes=node.stakes,
            state_delta=state_delta,
            excerpt=original_excerpt
        )

        if context:
            prompt = context + "\n\n" + prompt

        messages = [
            SystemMessage(content="You are a professional podcast storyteller."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()
