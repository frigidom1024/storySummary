"""测试完整分析流程"""
import os
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

# 启用 node_generator 调试日志
os.environ['DEBUG'] = 'node_generator'

import asyncio
from src.services.analyzer import Analyzer

async def test_full_analysis():
    """使用 wind.txt 全文测试完整分析"""
    book_id = 'wind-full-test'
    file_path = 'samples/wind.txt'

    # 检查文件
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"=== Full Analysis Test ===")
    print(f"File: {file_path}")
    print(f"Content length: {len(content)} chars")
    print()

    async def progress(p, msg):
        print(f"[{p}%] {msg}")

    analyzer = Analyzer()

    try:
        result = await analyzer.analyze(book_id, file_path, 'txt', progress)
        print(f"\n=== Result ===")
        print(f"Total chunks: {result['total_chunks']}")
        print(f"Total nodes: {result['total_nodes']}")
        print(f"Error: {result.get('error', 'None')}")

        # 检查保存的文件
        from src.storage.book_storage import BookStorage
        bs = BookStorage()
        nodes = bs.load_nodes(book_id)
        print(f"Saved nodes count: {len(nodes)}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_full_analysis())
