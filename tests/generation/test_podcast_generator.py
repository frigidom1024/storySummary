import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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

        with patch.object(generator.detail_recovery, 'enrich', new_callable=AsyncMock) as mock_enrich, \
             patch.object(generator.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_enrich.return_value = "A dark room with flickering candles casting dancing shadows"

            # Build a proper mock response
            mock_response = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "The room was dark, candles flickering against the walls..."
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            mock_create.return_value = mock_response

            text = await generator.generate_segment(current_node, "John walked into the dark room.")

        assert "dark" in text.lower()