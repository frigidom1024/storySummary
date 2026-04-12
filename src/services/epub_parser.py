"""EPUB file parser service."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import io

try:
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False


@dataclass
class EpubMetadata:
    """Extracted metadata from an EPUB file."""
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    cover_image: Optional[bytes] = None
    cover_extension: Optional[str] = None  # jpg/png


def parse_epub(file_bytes: bytes) -> EpubMetadata:
    """Parse an EPUB file and extract metadata.

    Args:
        file_bytes: Raw bytes of the EPUB file.

    Returns:
        EpubMetadata with extracted title, author, publisher, and cover.

    Raises:
        ValueError: If the file is not a valid EPUB.
    """
    if not HAS_EBOOKLIB:
        raise RuntimeError("ebooklib is not installed")

    try:
        book = epub.read_epub(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Invalid EPUB file: {e}")

    # Extract title
    title = None
    if book.get_metadata('DC', 'title'):
        title = book.get_metadata('DC', 'title')[0][0]
    elif book.get_metadata('OPF', 'title'):
        title = book.get_metadata('OPF', 'title')[0][0]

    # Extract author
    author = None
    if book.get_metadata('DC', 'creator'):
        author = book.get_metadata('DC', 'creator')[0][0]
    elif book.get_metadata('DC', 'author'):
        author = book.get_metadata('DC', 'author')[0][0]

    # Extract publisher
    publisher = None
    if book.get_metadata('DC', 'publisher'):
        publisher = book.get_metadata('DC', 'publisher')[0][0]

    # Extract cover image
    cover_image = None
    cover_extension = None

    for item in book.get_items():
        if item.get_type() == 9:  # MEDIA_TYPE.IMAGE
            item_href = item.get_name().lower()
            if 'cover' in item_href:
                cover_image = item.get_content()
                # Determine extension from MIME type or href
                if item.media_type:
                    ext = item.media_type.split('/')[-1]
                    if ext in ('jpeg', 'jpg', 'png', 'gif', 'webp'):
                        cover_extension = 'jpg' if ext == 'jpeg' else ext
                if not cover_extension:
                    cover_extension = 'png' if '.png' in item_href else 'jpg'
                break

    return EpubMetadata(
        title=title or '',
        author=author,
        publisher=publisher,
        cover_image=cover_image,
        cover_extension=cover_extension
    )
