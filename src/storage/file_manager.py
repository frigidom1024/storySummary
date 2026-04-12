"""Book file storage manager."""
import os
import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """Manages book files and cover images."""

    BASE_DIR = "data"
    BOOKS_DIR = os.path.join(BASE_DIR, "books")
    COVERS_DIR = os.path.join(BASE_DIR, "covers")

    def __init__(self):
        os.makedirs(self.BOOKS_DIR, exist_ok=True)
        os.makedirs(self.COVERS_DIR, exist_ok=True)

    def save_book_file(self, book_id: str, file_bytes: bytes, ext: str) -> str:
        """Save book file and return the path."""
        file_path = os.path.join(self.BASE_DIR, f"{book_id}.{ext}")
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        return file_path

    def get_book_file(self, book_id: str) -> Optional[tuple[str, str]]:
        """Get book file path and extension. Returns (path, ext) or None."""
        for ext in ['epub', 'txt']:
            file_path = os.path.join(self.BASE_DIR, f"{book_id}.{ext}")
            if os.path.exists(file_path):
                return file_path, ext
        return None

    def book_file_exists(self, book_id: str) -> bool:
        """Check if book file exists."""
        for ext in ['epub', 'txt']:
            if os.path.exists(os.path.join(self.BASE_DIR, f"{book_id}.{ext}")):
                return True
        return False

    def delete_book_file(self, book_id: str) -> bool:
        """Delete book file. Returns True if deleted."""
        deleted = False
        for ext in ['epub', 'txt']:
            file_path = os.path.join(self.BASE_DIR, f"{book_id}.{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted = True
        return deleted

    def save_cover(self, book_id: str, image_bytes: bytes, ext: str) -> Optional[str]:
        """Save cover image and return the URL path, or None if no image."""
        if not image_bytes:
            return None
        cover_path = os.path.join(self.COVERS_DIR, f"{book_id}.{ext}")
        with open(cover_path, 'wb') as f:
            f.write(image_bytes)
        return f"/api/covers/{book_id}.{ext}"

    def get_cover_url(self, book_id: str, ext: str) -> Optional[str]:
        """Get cover URL if exists."""
        cover_path = os.path.join(self.COVERS_DIR, f"{book_id}.{ext}")
        if os.path.exists(cover_path):
            return f"/api/covers/{book_id}.{ext}"
        return None

    def delete_cover(self, book_id: str) -> bool:
        """Delete all cover images for a book. Returns True if deleted."""
        deleted = False
        for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            cover_path = os.path.join(self.COVERS_DIR, f"{book_id}.{ext}")
            if os.path.exists(cover_path):
                os.remove(cover_path)
                deleted = True
        return deleted

    def cleanup_book_data(self, book_id: str) -> None:
        """Delete all files associated with a book (file, covers, nodes)."""
        self.delete_book_file(book_id)
        self.delete_cover(book_id)
        # Cleanup nodes directory
        nodes_dir = os.path.join(self.BOOKS_DIR, book_id)
        if os.path.exists(nodes_dir):
            shutil.rmtree(nodes_dir)


# Singleton instance
file_manager = FileManager()
