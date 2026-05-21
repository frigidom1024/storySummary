import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import uuid
import shutil
from unittest.mock import AsyncMock, patch, MagicMock
from src.writing.pipeline import ManuscriptPipeline
from src.models.chunk import Chunk
from src.models.narrative_node import NarrativeNode, CharacterState

def test_e2e_agent_with_mocked_llm():
    """End-to-end test with mocked LLM responses."""
    # Note: full_manuscript stores the POLISHED output from Phase 3,
    # which takes precedence over auto-built chapter manuscripts.
    unique_title = f"测试局外人E2E_{uuid.uuid4().hex[:8]}"
    output_dir = Path("output") / unique_title

    # Clean up any existing checkpoint
    if output_dir.exists():
        shutil.rmtree(output_dir)

    chunks = [
        Chunk(id="chunk-0001", text="今天妈妈死了。", order=0, chapter="第一部 Ⅰ"),
        Chunk(id="chunk-0002", text="第二天醒来是周六。", order=1, chapter="第一部 Ⅱ"),
    ]
    nodes = [
        NarrativeNode(
            id="n-0-0", parent_chunk_id="chunk-0001", beat_index=0,
            scene="养老院",
            situation="默尔索收到母亲去世的电报",
            turning_point="他不确定母亲去世的时间",
            emotional_arc="默尔索从漠然到微妙的困惑",
            mood_tone="疏离, 冷漠", narrative_rhythm="slow",
            narrative_role="opening",
            characters=[CharacterState(name="默尔索", state_before="漠然")]
        ),
        NarrativeNode(
            id="n-1-0", parent_chunk_id="chunk-0002", beat_index=0,
            scene="公寓",
            situation="默尔索醒来发现是周六",
            turning_point="想起老板对他请假的不满",
            emotional_arc="默尔索从困惑到接受",
            mood_tone="平静", narrative_rhythm="steady",
            narrative_role="rising",
            characters=[CharacterState(name="默尔索", state_before="困惑")]
        ),
    ]

    agent = PodcastWritingAgent(api_key="fake")

    # Mock the LLM responses - patch at class level since ainvoke is not a direct attribute
    mock_responses = [
        # Phase 1: planning
        MagicMock(content='{"chapters":[{"chunk_id":"chunk-0001","title":"开场","summary":"默尔索母亲去世"},{"chunk_id":"chunk-0002","title":"周六","summary":"默尔索的日常"}],"overall_tone":"疏离冷漠","core_themes":["存在主义","社会规则"]}'),
        # Phase 2: chapter 1
        MagicMock(content='这是第一章的播客稿...'),
        # Phase 2: chapter 2
        MagicMock(content='这是第二章的播客稿...'),
        # Phase 3: polish
        MagicMock(content='润色后的完整稿子。'),
    ]

    with patch('langchain_openai.ChatOpenAI.ainvoke', new_callable=AsyncMock) as mock_invoke:
        mock_invoke.side_effect = mock_responses

        import asyncio
        manuscript = asyncio.run(agent.run(chunks, nodes, unique_title))

        # Verify all 4 LLM calls were made (1 planning + 2 chapters + 1 polish)
        assert mock_invoke.call_count == 4, f"Expected 4 LLM calls, got {mock_invoke.call_count}"

        assert manuscript is not None
        assert manuscript.title == unique_title
        assert len(manuscript.chapters) == 2
        assert "润色后的完整稿子" in manuscript.full_manuscript