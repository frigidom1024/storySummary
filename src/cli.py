import asyncio
import argparse
import logging
from pathlib import Path
import os
import json
from dotenv import load_dotenv
from src.analysis.pipeline import NovelToPodcastPipeline
from src.logging_config import setup_logger


async def main():
    parser = argparse.ArgumentParser(description="Convert novels to podcast narratives")
    parser.add_argument("input_file", type=Path, help="Path to novel text file")
    parser.add_argument("--title", required=True, help="Story title")
    parser.add_argument("--user-id", default="default-user", help="User ID for multi-user isolation")
    parser.add_argument("--output", type=Path, help="Output JSON path")
    parser.add_argument("--db", type=Path, default=Path("story_data.db"), help="Database path")
    parser.add_argument("--vector-store", type=Path, default=Path("vector_store"), help="Vector store path")
    parser.add_argument("--model", type=str, default=None, help="LLM model (e.g., deepseek-chat, gpt-4o)")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    parser.add_argument("--log-file", type=Path, default=None, help="Log file path")

    args = parser.parse_args()

    # Setup logging
    log_level = getattr(logging, args.log_level)
    log_file = str(args.log_file) if args.log_file else None
    logger = setup_logger(level=log_level, log_file=log_file)

    load_dotenv()

    text = args.input_file.read_text(encoding="utf-8")

    # Support both DeepSeek and OpenAI
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")

    pipeline = NovelToPodcastPipeline(
        db_path=str(args.db),
        vector_store_path=str(args.vector_store),
        api_key=api_key,
        model=args.model,
        user_id=args.user_id,
    )

    result = await pipeline.process(text, title=args.title)

    if args.output:
        args.output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        logger.info(f"Output saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
