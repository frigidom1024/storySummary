"""Test OutlineAgent using BookRepository storage interface."""
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.writing.agents.outline import OutlineAgent
from src.storage.book_repository import BookRepository


async def main():
    book_id = "14669314-0ad6-4ca0-adcd-a1e1a0442e79"
    repo = BookRepository(base_dir="data")

    chunks = repo.load_chunks(book_id)
    nodes = repo.load_nodes(book_id)

    print(f"Loaded {len(chunks)} chunks, {len(nodes)} nodes")

    if not chunks:
        print("ERROR: No chunks found")
        return

    def progress_callback(msg: str):
        print(f"[PROGRESS] {msg}")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    agent = OutlineAgent(api_key=api_key, debug_mode=True)

    print("Starting outline generation...")
    result = await agent.build_outline(
        book_id=book_id,
        chunks=chunks,
        nodes=nodes,
        progress_callback=progress_callback,
        reference_script=None,
    )

    print("\n=== Outline Result ===")
    print(result)

    parsed = json.loads(result)
    print("\n=== Validation ===")
    print(f"story_synopsis: {parsed.get('story_synopsis', '')[:100]}...")
    print(f"total_sections: {parsed.get('metadata', {}).get('total_sections', 'N/A')}")
    print(f"manuscript_outline count: {len(parsed.get('manuscript_outline', []))}")


if __name__ == "__main__":
    asyncio.run(main())
