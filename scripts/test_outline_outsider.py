"""在已入库的《局外人》解析结果上跑 OutlineAgent，并在终端实时打印进度。

依赖：
- 环境变量 DEEPSEEK_API_KEY（或与项目一致的 LLM 配置）
- data/books/<book_id>/chunks.json 与 nodes.json 已由管线生成

示例：
  python scripts/test_outline_outsider.py
  python scripts/test_outline_outsider.py --book-id outsider -o output/outline_outsider.txt
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generation.outline_agent import OutlineAgent
from src.storage.book_storage import BookStorage


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="测试 OutlineAgent（已处理的局外人等书籍）")
    parser.add_argument(
        "--book-id",
        default="outsider",
        help="BookStorage 中的书籍 id（默认 outsider，对应 data/books/outsider/）",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="BookStorage 根目录（相对路径时相对于项目根目录）",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="将最终 outline 写入该文件（UTF-8）；不写则只打印路径提示",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="打开 OutlineAgent 的 debug 模式",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir

    storage = BookStorage(base_dir=str(data_dir))
    book_dir = storage.books_dir / args.book_id
    chunks_path = book_dir / "chunks.json"
    nodes_path = book_dir / "nodes.json"

    chunks = storage.load_chunks(args.book_id)
    nodes = storage.load_nodes(args.book_id)

    def log(msg: str) -> None:
        print(f"[{_ts()}] {msg}", flush=True)

    if not chunks:
        log(f"错误：未找到 chunks，请确认文件存在：{chunks_path}")
        log("若尚未入库，请先对《局外人》跑完整解析管线，或改用正确的 --book-id。")
        sys.exit(1)
    if not nodes:
        log(f"警告：nodes 为空，节点线索将缺失。路径：{nodes_path}")

    log(f"已加载 book_id={args.book_id} chunks={len(chunks)} nodes={len(nodes)}")
    log("开始生成 outline（阶段1 逐章摘要 + 阶段2 Agent 优化）…")

    async def run() -> str:
        agent = OutlineAgent(debug_mode=args.debug)
        return await agent.build_outline(
            book_id=args.book_id,
            chunks=chunks,
            nodes=nodes,
            progress_callback=log,
        )

    try:
        outline = asyncio.run(run())
    except KeyboardInterrupt:
        log("已中断")
        sys.exit(130)
    except Exception as exc:
        log(f"失败：{exc}")
        raise

    if not outline.strip():
        log("错误：outline 为空")
        sys.exit(1)

    log(f"成功：outline 长度 {len(outline)} 字符")

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(outline, encoding="utf-8")
        log(f"已写入 {out_path}")


if __name__ == "__main__":
    main()
