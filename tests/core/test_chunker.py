import pytest
from src.core.chunker import TextChunker, ChapterChunker


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


class TestChapterChunker:
    def test_extracts_chapters(self):
        text = "Chapter 1\n\nContent one.\n\nChapter 2\n\nContent two."
        chunker = ChapterChunker()
        chunks = chunker.chunk(text)
        assert len(chunks) == 2
        assert chunks[0].chapter == "Chapter 1"
        assert chunks[1].chapter == "Chapter 2"