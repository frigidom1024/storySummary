import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import AIMessage
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode
from src.core.node_generator import NarrativeNodeGenerator


class TestNarrativeNodeGenerator:
    @pytest.mark.asyncio
    async def test_generates_multiple_beats_from_chunk(self):
        """One chunk → multiple narrative beats (multi-beat extraction)."""
        generator = NarrativeNodeGenerator(api_key="test-key")
        chunk = Chunk(id="c-001", text="John walked in. He was scared. Then he saw something.", order=0)

        mock_content = '''[
          {"id":"n-0000-0","parent_chunk_id":"c-001","beat_index":0,"scene":"A room","characters":[{"name":"John","state":"calm","goal":"enter"}],"event":"John walks in","dialogue_summary":"","tension":"","stakes":"","foreshadow":"","narrative_role":"opening"},
          {"id":"n-0000-1","parent_chunk_id":"c-001","beat_index":1,"scene":"A room","characters":[{"name":"John","state":"scared","goal":"understand situation"}],"event":"John sees something","dialogue_summary":"","tension":"fear","stakes":"safety","foreshadow":"","narrative_role":"rising"}
        ]'''

        # Patch at class level with spec to avoid Pydantic issues
        with patch('langchain_openai.chat_models.base.ChatOpenAI.ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=mock_content)
            nodes = await generator.generate_from_chunk(chunk)

        # Returns a LIST of nodes, not single node
        assert isinstance(nodes, list)
        assert len(nodes) == 2
        assert nodes[0].id == "n-0000-0"
        assert nodes[1].id == "n-0000-1"
        assert nodes[0].parent_chunk_id == "c-001"
        assert nodes[1].beat_index == 1
        assert nodes[0].characters[0].name == "John"
        assert nodes[1].characters[0].state == "scared"

    @pytest.mark.asyncio
    async def test_single_beat_still_returns_list(self):
        """Even a single beat returns a list for consistent handling."""
        generator = NarrativeNodeGenerator(api_key="test-key")
        chunk = Chunk(id="c-002", text="Simple sentence.", order=1)

        mock_content = '{"id":"n-0001-0","parent_chunk_id":"c-002","beat_index":0,"scene":"A place","characters":[],"event":"Something happens","dialogue_summary":"","tension":"","stakes":"","foreshadow":"","narrative_role":""}'

        with patch('langchain_openai.chat_models.base.ChatOpenAI.ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=mock_content)
            nodes = await generator.generate_from_chunk(chunk)

        assert isinstance(nodes, list)
        assert len(nodes) == 1
