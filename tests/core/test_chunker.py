import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from src.utils.reader.text import TextChunker, AdaptiveChunker


class TestTextChunker:
    def test_split_by_paragraphs(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunker = TextChunker(chunk_size=1)
        chunks = chunker.chunk(text)
        assert len(chunks) == 3
        assert chunks[0].text == "Paragraph one."

    def test_combines_small_paragraphs(self):
        text = "Short.\n\nAlso short."
        chunker = TextChunker(chunk_size=2)
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert "Short" in chunks[0].text


class TestAdaptiveChunker:
    def test_extracts_chapters(self):
        text = "Chapter 1\n\nContent one.\n\nChapter 2\n\nContent two."
        chunker = AdaptiveChunker()
        chunks = chunker.chunk(text)
        assert len(chunks) == 2
        assert chunks[0].chapter == "Chapter 1"
        assert chunks[1].chapter == "Chapter 2"

    def test_extracts_chapters_with_roman_numerals(self):
        text = "Chapter I\n\nContent one.\n\nChapter IV\n\nContent two."
        chunker = AdaptiveChunker()
        chunks = chunker.chunk(text)
        assert len(chunks) == 2
        assert chunks[0].chapter == "Chapter I"
        assert chunks[1].chapter == "Chapter IV"



if __name__ == "__main__":
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from src.utils.reader.text import AdaptiveChunker

    # Test with wind sample
    wind_path = Path(__file__).parent.parent.parent / 'samples' / 'wind'
    with open(wind_path, 'r', encoding='utf-8') as f:
        text = f.read()

    chunker = AdaptiveChunker()
    chunks = chunker.chunk(text)

    print(f"Wind sample: {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: chapter={chunk.chapter or 'None'}, len={len(chunk.text)}")
     