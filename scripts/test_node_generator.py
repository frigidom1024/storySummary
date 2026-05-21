"""测试节点生成逻辑 - 不使用工具调用"""
import os
import sys
from dotenv import load_dotenv

# 确保加载根目录的 .env
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

import asyncio
from langchain_openai import ChatOpenAI
from src.analysis.node_generator import NarrativeNodeGenerator
from src.models.chunk import Chunk
from src.prompts.base_node import BASE_NODE_PROMPT
from src.logging_config import debug

# 直接使用 LLM 测试，不走完整的 node_generator
async def test_direct_llm():
    """直接测试 LLM 输出 JSON"""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(root_dir, ".env"))

    api_key = os.getenv("DEEPSEEK_API_KEY")
    api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url=api_base,
        temperature=0.3  # 降低温度减少随机性
    )

    test_text = """
李明收到了一封神秘的邀请函，邀请他参加一个在偏远山区别墅举行的聚会。邀请函上没有署名，只有一个奇怪的符号。李明虽然感到疑惑，但出于好奇，他还是决定前往。

当他到达别墅时，发现已经有几位客人抵达。他们分别是：退休的侦探张大爷、年轻的记者小王、神秘的女子陈小姐，以及别墅的主人——一位富有的商人王先生。大家互相寒暄后，王先生宣布了一个惊人的消息：他的女儿三天前在这座别墅里消失了。
    """

    prompt = BASE_NODE_PROMPT.format(
        text=test_text.strip(),
        chunk_order=0,
        last_nodes="（这是第一个chunk，无前序节点）",
        beat_index=0
    )

    print("=== Direct LLM Test ===")
    print(f"API Key: {api_key[:10]}...")
    print(f"API Base: {api_base}")
    print(f"Text length: {len(test_text)}")
    print()

    # 直接调用 LLM
    messages = [
        ("system", "你是一个专业的小说场记师。直接输出JSON数组，不要解释，不要调用工具。输出格式：[{{\"id\": \"n-0-0\", \"beat_index\": 0, ...}}]"),
        ("human", prompt)
    ]

    print("Calling LLM...")
    response = await llm.ainvoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)

    print(f"Response length: {len(content)}")
    print(f"Response content:\n{content[:1000]}")
    print()

    # 尝试解析 JSON
    import json
    import re

    # 提取 JSON 数组
    json_match = re.search(r'\[\s*\{', content)
    if json_match:
        start = json_match.start()
        depth = 0
        for i, c in enumerate(content[start:]):
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
            if depth == 0:
                try:
                    data = json.loads(content[start:start+i+1])
                    print(f"Parsed {len(data)} nodes!")
                    for node in data[:3]:
                        print(f"  - {node.get('id')}: {node.get('scene', '')[:50]}")
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                break
    else:
        print("No JSON array found in response")


async def test_node_generator():
    """测试节点生成（使用完整流程）"""
    test_text = """
李明收到了一封神秘的邀请函，邀请他参加一个在偏远山区别墅举行的聚会。邀请函上没有署名，只有一个奇怪的符号。李明虽然感到疑惑，但出于好奇，他还是决定前往。

当他到达别墅时，发现已经有几位客人抵达。他们分别是：退休的侦探张大爷、年轻的记者小王、神秘的女子陈小姐，以及别墅的主人——一位富有的商人王先生。大家互相寒暄后，王先生宣布了一个惊人的消息：他的女儿三天前在这座别墅里消失了。
    """

    print("=== Node Generator Test ===")
    print(f"Test text length: {len(test_text)} chars")
    print(f"API Key available: {bool(os.getenv('DEEPSEEK_API_KEY'))}")
    print()

    # 创建节点生成器
    generator = NarrativeNodeGenerator()
    print(f"LLM initialized: {generator.llm is not None}")
    print(f"Model: {generator.model_name}")
    print()

    # 创建 Chunk 对象
    chunk = Chunk(id="test-001", text=test_text.strip(), order=0)

    # 生成节点
    print("Generating nodes...")
    try:
        nodes = await generator.generate_from_chunk(chunk)
        print(f"Generated {len(nodes)} nodes")
        print()

        if nodes:
            print("=== Sample Node ===")
            node = nodes[0]
            for key in ['id', 'beat_index', 'scene', 'characters', 'importance']:
                if key in node:
                    val = node[key]
                    if isinstance(val, str) and len(val) > 50:
                        val = val[:50] + "..."
                    print(f"  {key}: {val}")
        else:
            print("No nodes generated - check warnings above")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # 先测试直接 LLM
    asyncio.run(test_direct_llm())
    print("\n" + "="*50 + "\n")
    # 再测试完整流程
    asyncio.run(test_node_generator())
