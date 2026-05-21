import asyncio
import os
import sys

os.environ['DEEPSEEK_API_KEY'] = 'sk-4ff06504656a45c9b4b60adfdaa16d5c'
os.environ['DEEPSEEK_API_BASE'] = 'https://api.deepseek.com/v1'

# 设置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

from src.writing.pipeline import ManuscriptPipeline

async def test():
    book_id = "66ffedc5-fd54-43ff-acb7-879876243c94"

    pipeline = ManuscriptPipeline(
        output_dir="output",
        debug_mode=False,  # 禁用 debug 避免编码问题
    )

    result = await pipeline.run(book_id)

    print(f"Title: {result.title}")
    print(f"Phase: {result.phase}")
    print(f"Chapters written: {result.chapters_written}/{result.total_chunks}")
    print(f"Has intro: {bool(result.intro)}")
    print(f"Has reflection: {bool(result.reflection)}")
    print(f"Manuscript length: {len(result.full_manuscript)} chars")

if __name__ == '__main__':
    asyncio.run(test())