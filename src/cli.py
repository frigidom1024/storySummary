import asyncio
import argparse
from pathlib import Path
import os
import json
from dotenv import load_dotenv
from src.pipeline import NovelToPodcastPipeline


async def main():
    parser = argparse.ArgumentParser(description="Convert novels to podcast narratives")
    parser.add_argument("input_file", type=Path, help="Path to novel text file")
    parser.add_argument("--title", required=True, help="Story title")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    parser.add_argument("--db", type=Path, default=Path("story_data.db"), help="Database path")
    parser.add_argument("--vector-store", type=Path, default=Path("vector_store"), help="Vector store path")
    parser.add_argument("--model", type=str, default=None, help="LLM model (e.g., deepseek-chat, gpt-4o)")

    args = parser.parse_args()

    load_dotenv()

    text = args.input_file.read_text(encoding="utf-8")

    # Support both DeepSeek and OpenAI
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")

    pipeline = NovelToPodcastPipeline(
        db_path=str(args.db),
        vector_store_path=str(args.vector_store),
        api_key=api_key,
        model=args.model
    )

    result = await pipeline.process(text, title=args.title)

    if args.output:
        args.output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(f"Processed {len(result['nodes'])} nodes")
    print(f"Structure: {result['structure'].model_dump()}")


if __name__ == "__main__":
    asyncio.run(main())
