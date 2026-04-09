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
            f"{c.name} (进入场景时: {c.state_before})" for c in node.characters
        ])

    def _format_discussion_prompts(self, node: NarrativeNode) -> str:
        if not node.discussion_prompts:
            return ""
        return "讨论锚点:\n" + "\n".join([f"- {p}" for p in node.discussion_prompts])

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
            situation=node.situation,
            excerpt=original_excerpt
        )

        # Step 2: Build context from previous nodes
        context = ""
        if prev_node:
            context = f"上一节点: {prev_node.scene}。情况: {prev_node.situation}\n"
        if context_nodes:
            context += "更早的节点:\n" + "\n".join([
                f"- {n.scene}: {n.situation}" for n in context_nodes[-2:]
            ])

        # Step 3: Format discussion prompts
        discussion = self._format_discussion_prompts(node)

        # Step 4: Generate podcast with all context
        prompt = PODCAST_GENERATION_PROMPT.format(
            scene=enriched_scene,
            characters=self._format_characters(node),
            situation=node.situation,
            turning_point=node.turning_point,
            emotional_arc=node.emotional_arc,
            mood_tone=node.mood_tone,
            rhythm=node.narrative_rhythm,
            excerpt=original_excerpt
        )

        if context:
            prompt = context + "\n\n" + prompt
        if discussion:
            prompt = prompt + "\n\n" + discussion

        messages = [
            SystemMessage(content="You are a professional podcast storyteller."),
            HumanMessage(content=prompt)
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()
