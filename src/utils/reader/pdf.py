"""
PDF file reader utility.
Extracts text and metadata from PDF files.
"""
from pathlib import Path

from src.utils.reader import BookReader


class PdfReader(BookReader):
    """Read PDF files and extract text content."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self._text: str = ""
        self._title: str = ""
        self._author: str = ""
        self._chapters: list[dict] = []
        self._metadata: dict = {}
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
            self._metadata = {
                "title": self._title,
                "author": self._author,
            }
        else:
            self._title = self.pdf_path.stem
            self._author = "Unknown"
            self._metadata = {}

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

    @property
    def metadata(self) -> dict:
        return self._metadata
