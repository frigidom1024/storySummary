import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import AIMessage
from src.writing.agents.writer import ChapterWriter
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

        # Mock generate_segment to return a pre-determined text
        mock_text = "The room was dark, candles flickering against the walls..."
        with patch.object(generator, 'generate_segment', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_text
            text = await generator.generate_segment(current_node, "John walked into the dark room.")

        assert "dark" in text.lower()
