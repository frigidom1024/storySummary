import pytest
import tempfile
import shutil
import os
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from src.pipeline import NovelToPodcastPipeline


class TestPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_multi_beat(self):
        # Use temp directories for ChromaDB (doesn't support :memory: for PersistentClient)
        temp_dir = tempfile.mkdtemp()
        db_path = tempfile.mktemp(suffix='.db')
        vector_store_path = temp_dir

        try:
            pipeline = NovelToPodcastPipeline(
                db_path=db_path,
                vector_store_path=vector_store_path,
                api_key="test-key"
            )

            novel_text = """
            Chapter 1

            John walked into the dark room. His heart pounded. Then he heard a noise.
            """

            # Multi-beat returns a list of nodes
            mock_content = '''[
              {"id":"n-0001-0","parent_chunk_id":"chunk-0000","beat_index":0,"scene":"A dark room","characters":[{"name":"John","state":"scared","goal":"find light"}],"event":"John enters dark room","dialogue_summary":"","tension":"danger","stakes":"life","foreshadow":"","narrative_role":"opening"},
              {"id":"n-0001-1","parent_chunk_id":"chunk-0000","beat_index":1,"scene":"A dark room","characters":[{"name":"John","state":"terrified","goal":"identify noise"}],"event":"John hears a noise","dialogue_summary":"","tension":"immediate threat","stakes":"life","foreshadow":"","narrative_role":"rising"}
            ]'''

            with patch('langchain_openai.chat_models.base.ChatOpenAI.ainvoke', new_callable=AsyncMock) as mock_ainvoke:
                mock_ainvoke.return_value = AIMessage(content=mock_content)
                result = await pipeline.process(novel_text, title="Test Story")

            # Should have 2 nodes from 1 chunk (multi-beat)
            assert len(result["nodes"]) == 2
            assert result["nodes"][0].prev_node_id == ""
            assert result["nodes"][1].prev_node_id == "n-0001-0"
            assert result["nodes"][1].state_delta != ""
            assert result["structure"] is not None
        finally:
            # Clean up - close db connection first on Windows
            pipeline.db = None
            shutil.rmtree(temp_dir, ignore_errors=True)
            if os.path.exists(db_path):
                try:
                    os.unlink(db_path)
                except PermissionError:
                    pass  # Windows file locking issue, ignore
