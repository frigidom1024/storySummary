import pytest
import shutil
from pathlib import Path

# Clear test book data before each test to ensure isolation
@pytest.fixture(autouse=True)
def clear_test_book_data():
    """Clear the test-book data before each test to ensure test isolation."""
    test_book_dir = Path("data/books/test-book")
    if test_book_dir.exists():
        shutil.rmtree(test_book_dir)
    yield
    # Cleanup after test as well
    if test_book_dir.exists():
        shutil.rmtree(test_book_dir)