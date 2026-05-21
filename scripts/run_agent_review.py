import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.writing.agents.outline import OutlineAgent
from src.writing.agents.style import StyleLearningAgent
from src.storage.book_storage import BookStorage


async def run(
    book_id: str,
    reference_script_path: str,
    output_root: str,
    outline_timeout: int,
    style_timeout: int,
) -> Path:
    load_dotenv()

    storage = BookStorage()
    chunks = storage.load_chunks(book_id)
    nodes = storage.load_nodes(book_id)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(output_root) / f"{book_id}-{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    input_summary = {
        "book_id": book_id,
        "chunks_count": len(chunks),
        "nodes_count": len(nodes),
        "reference_script_path": reference_script_path,
        "created_at": datetime.now().isoformat(),
    }
    (out_dir / "input_summary.json").write_text(
        json.dumps(input_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    outline_status = "not_run"
    style_status = "not_run"
    outline_output = ""
    style_output = ""
    outline_error = ""
    style_error = ""

    try:
        outliner = OutlineAgent(debug_mode=False)
        outline_output = await asyncio.wait_for(
            outliner.build_outline(book_id=book_id, chunks=chunks, nodes=nodes),
            timeout=outline_timeout,
        )
        (out_dir / "outline_output.txt").write_text(outline_output, encoding="utf-8")
        outline_status = "success"
    except Exception as exc:
        outline_error = str(exc) or f"{type(exc).__name__}: {repr(exc)}"
        (out_dir / "outline_error.txt").write_text(outline_error, encoding="utf-8")
        outline_status = "failed"

    try:
        ref_text = Path(reference_script_path).read_text(encoding="utf-8")
    except Exception as exc:
        ref_text = ""
        style_error = f"read_reference_failed: {exc}"

    if ref_text:
        try:
            style_agent = StyleLearningAgent(debug_mode=False)
            style_output = await asyncio.wait_for(
                style_agent.learn(ref_text),
                timeout=style_timeout,
            )
            (out_dir / "style_output.txt").write_text(style_output, encoding="utf-8")
            style_status = "success"
        except Exception as exc:
            style_error = str(exc) or f"{type(exc).__name__}: {repr(exc)}"
            (out_dir / "style_error.txt").write_text(style_error, encoding="utf-8")
            style_status = "failed"
    else:
        style_status = "failed"
        if not style_error:
            style_error = "reference_script_empty"
        (out_dir / "style_error.txt").write_text(style_error, encoding="utf-8")

    report = {
        "outline_status": outline_status,
        "style_status": style_status,
        "outline_output_file": str(out_dir / "outline_output.txt"),
        "style_output_file": str(out_dir / "style_output.txt"),
        "outline_error_file": str(out_dir / "outline_error.txt"),
        "style_error_file": str(out_dir / "style_error.txt"),
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = [
        "# Agent Review Report",
        "",
        f"- book_id: `{book_id}`",
        f"- chunks: `{len(chunks)}`",
        f"- nodes: `{len(nodes)}`",
        f"- outline status: `{outline_status}`",
        f"- style status: `{style_status}`",
    ]
    if outline_error:
        md.extend(["", "## Outline Error", outline_error])
    if style_error:
        md.extend(["", "## Style Error", style_error])
    (out_dir / "report.md").write_text("\n".join(md), encoding="utf-8")

    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run outline/style agents and persist outputs")
    parser.add_argument("--book-id", required=True, help="Book id that already has chunks/nodes")
    parser.add_argument("--reference-script", required=True, help="Reference script txt path")
    parser.add_argument("--output-root", default="output/agent_checks", help="Output directory root")
    parser.add_argument("--outline-timeout", type=int, default=180, help="Outline agent timeout seconds")
    parser.add_argument("--style-timeout", type=int, default=180, help="Style agent timeout seconds")
    args = parser.parse_args()

    out_dir = asyncio.run(
        run(
            args.book_id,
            args.reference_script,
            args.output_root,
            args.outline_timeout,
            args.style_timeout,
        )
    )
    print(str(out_dir))


if __name__ == "__main__":
    main()
