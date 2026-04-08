import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from src.generation.podcast_generator import PodcastGenerator
from src.models.narrative_node import NarrativeNode, CharacterState


class TestPodcastGenerator:
    @pytest.mark.asyncio
    async def test_generates_podcast_segment(self):
        generator = PodcastGenerator(api_key="test-key")

        current_node = NarrativeNode(
            id="n-001",
            scene="A dark room with flickering candles",
            characters=[CharacterState(name="John", state="nervous", goal="find the exit")],
            event="John enters a dark room and hears a noise",
            dialogue_summary="",
            tension="Something lurks in the shadows",
            stakes="John's life is at risk",
            narrative_role="rising"
        )

        with patch('langchain_openai.chat_models.base.ChatOpenAI.ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content="The room was dark, candles flickering against the walls...")

            # Also need to mock detail_recovery
            with patch.object(generator.detail_recovery.llm, 'ainvoke', new_callable=AsyncMock) as mock_detail:
                mock_detail.return_value = AIMessage(content="A dark room with flickering candles casting dancing shadows")
                text = await generator.generate_segment(current_node, "John walked into the dark room.")

        assert "dark" in text.lower()
