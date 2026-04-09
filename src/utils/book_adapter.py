"""
Book adapter for extracting text from EPUB and PDF files.
Provides a unified interface for the pipeline to process different book formats.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BookReader(ABC):
    """Abstract base class for book readers."""

    @abstractmethod
    def read(self) -> str:
        """Read book and return full text content."""
        ...

    @property
    @abstractmethod
    def title(self) -> str:
        """Return book title."""
        ...

    @property
    @abstractmethod
    def author(self) -> str:
        """Return book author."""
        ...

    @property
    def chapters(self) -> list[dict]:
        """Return list of chapters with title and content."""
        return []


class EpubBookReader(BookReader):
    """Read EPUB files."""

    def __init__(self, epub_path: str):
        from src.utils.epub_reader import EpubReader as _EpubReader
        self._reader = _EpubReader(epub_path)

    def read(self) -> str:
        return self._reader.read()

    @property
    def title(self) -> str:
        return self._reader.title

    @property
    def author(self) -> str:
        return self._reader.author

    @property
    def chapters(self) -> list[dict]:
        return self._reader.chapters


class PdfBookReader(BookReader):
    """Read PDF files and extract text content."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self._text: str = ""
        self._title: str = ""
        self._author: str = ""
        self._chapters: list[dict] = []
        self._load_pdf()

    def _load_pdf(self):
        """Load PDF and extract text."""
        try:
            import pypdf
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                raise ImportError(
                    "pypdf or PyPDF2 is required for PDF reading. "
                    "Install with: pip install pypdf"
                )

        try:
            from pypdf import PdfReader as _PdfReader
            reader = _PdfReader(self.pdf_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF: {e}")

        # Extract metadata
        if reader.metadata:
            self._title = str(reader.metadata.get("/Title", "")).strip() or self.pdf_path.stem
            self._author = str(reader.metadata.get("/Author", "")).strip() or "Unknown"
        else:
            self._title = self.pdf_path.stem
            self._author = "Unknown"

        # Extract text page by page
        full_text_parts = []
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                # Add page marker for chapter detection
                full_text_parts.append(f"\n\n## Page {page_num + 1}\n\n{text}")

        self._text = "".join(full_text_parts)

        # Try to detect chapters from PDF structure
        self._detect_chapters()

    def _detect_chapters(self):
        """Detect chapters from PDF text content."""
        import re

        # Common chapter patterns
        chapter_patterns = [
            # 第X章 / 第X节 / 第X部
            re.compile(r'第\s*[0-9零一二三四五六七八九十百千万]+\s*[章节部篇]'),
            # Chapter X / CHAPTER X
            re.compile(r'Chapter\s+\d+', re.IGNORECASE),
            # 一、 二、 三、 (outline numbering)
            re.compile(r'^[一二三四五六七八九十百千]+、', re.MULTILINE),
        ]

        paragraphs = [p.strip() for p in self._text.split("\n\n") if p.strip()]
        current_chapter = None
        current_content = []

        for para in paragraphs:
            has_chapter = False
            for pattern in chapter_patterns:
                if pattern.search(para):
                    has_chapter = True
                    break

            if has_chapter:
                if current_content:
                    self._chapters.append({
                        "title": current_chapter or f"Chapter {len(self._chapters) + 1}",
                        "content": "\n\n".join(current_content),
                        "order": len(self._chapters)
                    })
                    current_content = []
                # Use first line as chapter title
                first_line = para.split("\n")[0][:100]
                current_chapter = first_line.strip()
                # Rest of paragraph (if multi-line)
                rest = "\n".join(para.split("\n")[1:]).strip()
                if rest:
                    current_content.append(rest)
            else:
                current_content.append(para)

        # Don't forget last chapter
        if current_content:
            self._chapters.append({
                "title": current_chapter or f"Chapter {len(self._chapters) + 1}",
                "content": "\n\n".join(current_content),
                "order": len(self._chapters)
            })

    def read(self) -> str:
        return self._text

    @property
    def title(self) -> str:
        return self._title

    @property
    def author(self) -> str:
        return self._author

    @property
    def chapters(self) -> list[dict]:
        return self._chapters


def read_book(book_path: str) -> BookReader:
    """
    Auto-detect book format and return appropriate reader.
    Supported formats: .epub, .pdf
    """
    path = Path(book_path)
    suffix = path.suffix.lower()

    if suffix == ".epub":
        return EpubBookReader(book_path)
    elif suffix == ".pdf":
        return PdfBookReader(book_path)
    else:
        raise ValueError(f"Unsupported book format: {suffix}. Supported: .epub, .pdf")
