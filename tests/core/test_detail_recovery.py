import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.detail_recovery import DetailRecovery


class TestDetailRecovery:
    @pytest.mark.asyncio
    async def test_enriches_node_with_details(self):
        recovery = DetailRecovery(api_key="test-key")
        excerpt = "The rain hammered against the window. John shivered, his teeth chattering."

        expected_content = 'Rain lashed against the grimy window as John shuddered, his teeth clicking together involuntarily.'

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=expected_content))]

        mock_completions = AsyncMock()
        mock_completions.create = AsyncMock(return_value=mock_response)

        mock_chat = MagicMock()
        mock_chat.completions = mock_completions

        with patch.object(recovery.client, 'chat', mock_chat):
            enriched = await recovery.enrich(
                scene="Inside a room",
                characters="John (cold, wanting warmth)",
                event="John felt cold",
                excerpt=excerpt
            )

        assert "rain" in enriched.lower()
        assert "shuddered" in enriched.lower()