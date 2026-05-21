import pytest
from src.writing.models import Draft, DraftSection

def test_podcast_manuscript_creation():
    manuscript = PodcastManuscript(
        title="神的九十亿个名字",
        author="阿瑟·克拉克",
        chapters=[
            ChapterManuscript(
                chunk_id="chunk-0001",
                title="引言",
                manuscript="哈喽，大家好..."
            )
        ]
    )
    assert manuscript.title == "神的九十亿个名字"
    assert len(manuscript.chapters) == 1
    assert "哈喽" in manuscript.full_manuscript

def test_full_manuscript_concatenation():
    manuscript = PodcastManuscript(
        title="Test",
        author="Author",
        chapters=[
            ChapterManuscript(chunk_id="c1", title="第1章", manuscript="第一章内容"),
            ChapterManuscript(chunk_id="c2", title="第2章", manuscript="第二章内容"),
        ]
    )
    assert "第一章内容" in manuscript.full_manuscript
    assert "第二章内容" in manuscript.full_manuscript
    # Should have chapter separator
    assert "第1章" in manuscript.full_manuscript