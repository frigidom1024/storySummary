import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from src.analysis.detail_recovery import DetailRecovery


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
                situation="John needs warmth",
                excerpt=excerpt
            )

        assert "rain" in enriched.lower()
        assert "shuddered" in enriched.lower()


if __name__ == "__main__":
    import asyncio
    import json
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv()

    from src.analysis.detail_recovery import DetailRecovery

    async def test_wind_sample():
        recovery = DetailRecovery()

        excerpt = """下午三点四十七分，手机震了一下。他掏出来看了一眼，是母亲发来的语音。他没点开，光看转成文字的那行字就知道内容："小屿，你爸问你工作找得怎么样了，隔壁李阿姨儿子进了……"

他按灭屏幕，把手机塞回裤兜。

书店里开着老式吊扇，嗡嗡地转，吹得墙上的海报边角翻动。收银台后面坐着一个头发花白的老人，戴着老花镜在看一份《参考消息》，偶尔端起搪瓷缸子喝一口茶，发出很大的咕咚声。"""

        scene = "青岛路旧书店，下午三点多"
        characters = "陈屿（无聊、逃避现实），书店老人（平静、专注）"
        situation = "陈屿需要一个地方消磨时间"

        print("Testing DetailRecovery...")
        print(f"Scene: {scene}")
        print(f"Characters: {characters}")
        print(f"Situation: {situation}")
        print("-" * 60)

        enriched = await recovery.enrich(
            scene=scene,
            characters=characters,
            situation=situation,
            excerpt=excerpt
        )

        # Save to file to avoid encoding issues
        output_path = Path(__file__).parent.parent.parent / 'detail_recovery_output.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Input:\n")
            f.write(f"Scene: {scene}\n")
            f.write(f"Characters: {characters}\n")
            f.write(f"Situation: {situation}\n")
            f.write(f"Excerpt: {excerpt}\n")
            f.write(f"\nOutput:\n{enriched}\n")
        print(f"Saved to {output_path}")

    asyncio.run(test_wind_sample())