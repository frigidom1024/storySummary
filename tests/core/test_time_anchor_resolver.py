import pytest
from src.core.time_anchor_resolver import TimeAnchorResolver, TimeAnchorResult


def test_time_anchor_result_model():
    result = TimeAnchorResult(
        node_id="n-0-0",
        time_type="present",
        relative_to_prev="continue",
        anchor_hint="现在",
        confidence=0.9,
    )
    assert result.node_id == "n-0-0"
    assert result.time_type == "present"


@pytest.mark.asyncio
async def test_resolver_returns_defaults_without_llm():
    resolver = TimeAnchorResolver()
    resolver.llm = None
    nodes = [{"id": "n-0-0", "scene": "test"}]
    results = await resolver.resolve(nodes)
    assert len(results) == 1
    assert results[0].node_id == "n-0-0"
