import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from src.core.detail_recovery import DetailRecovery


class TestDetailRecovery:
    @pytest.mark.asyncio
    async def test_enriches_node_with_details(self):
        recovery = DetailRecovery(api_key="test-key")
        excerpt = "The rain hammered against the window. John shivered, his teeth chattering."

        expected_content = 'Rain lashed against the grimy window as John shuddered, his teeth clicking together involuntarily.'

        with patch('langchain_openai.chat_models.base.ChatOpenAI.ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = AIMessage(content=expected_content)
            enriched = await recovery.enrich(
                scene="Inside a room",
                characters="John (cold, wanting warmth)",
                event="John felt cold",
                excerpt=excerpt
            )

        assert "rain" in enriched.lower()
        assert "shuddered" in enriched.lower()
