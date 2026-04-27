# ManuscriptRepository 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `ManuscriptRepository` 类，提供口播稿工作流成果的存储和访问接口。

**Architecture:** 在 `src/storage/` 下创建 `manuscript_repository.py`，复用 `BookRepository` 的路径构建逻辑。

**Tech Stack:** Python, JSON, 文件系统

---

## 任务总览

| Task | 描述 |
|------|------|
| 1 | 创建 ManuscriptRepository 类骨架 |
| 2 | 实现故事梗概相关方法 |
| 3 | 实现口播稿大纲相关方法 |
| 4 | 实现章节草稿相关方法 |
| 5 | 实现最终口播稿相关方法 |
| 6 | 实现工具方法（delete/manuscript_exists） |
| 7 | 验证功能正确性 |

---

## Task 1: 创建 ManuscriptRepository 类骨架

**Files:**
- Create: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 创建文件并定义类骨架**

```python
"""口播稿仓储接口 - 管理口播稿工作流成果的存储"""

import json
import os
import tempfile
from pathlib import Path

from src.storage.json_storage import JsonStorage


class ManuscriptRepository:
    """口播稿仓储 - 管理口播稿工作流成果的存储"""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.books_dir = self.base_dir / "books"
        self.json_storage = JsonStorage()

    # === 路径构建 ===

    def _book_dir(self, book_id: str) -> Path:
        """获取书籍目录路径"""
        return self.books_dir / book_id

    def _synopsis_file(self, book_id: str) -> Path:
        """获取 synopsis.json 路径"""
        return self._book_dir(book_id) / "synopsis.json"

    def _outline_file(self, book_id: str) -> Path:
        """获取 outline.json 路径"""
        return self._book_dir(book_id) / "outline.json"

    def _drafts_file(self, book_id: str) -> Path:
        """获取 chapter_drafts.json 路径"""
        return self._book_dir(book_id) / "chapter_drafts.json"

    def _final_manuscript_file(self, book_id: str) -> Path:
        """获取 final_manuscript.txt 路径"""
        return self._book_dir(book_id) / "final_manuscript.txt"

    # === 原子写入 ===

    def _write_json(self, file_path: Path, data) -> None:
        """原子写入 JSON 文件"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=file_path.parent)
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, file_path)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile src/storage/manuscript_repository.py`
Expected: 无输出（成功）

- [ ] **Step 3: 提交**

```bash
git add src/storage/manuscript_repository.py
git commit -m "feat(storage): create ManuscriptRepository class skeleton"
```

---

## Task 2: 实现故事梗概相关方法

**Files:**
- Modify: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 添加 synopsis 相关方法**

在类中添加：

```python
def save_synopsis(self, book_id: str, synopsis: str) -> None:
    """保存故事梗概"""
    data = {"synopsis": synopsis}
    self._write_json(self._synopsis_file(book_id), data)

def load_synopsis(self, book_id: str) -> str | None:
    """加载故事梗概"""
    file_path = self._synopsis_file(book_id)
    if not file_path.exists():
        return None
    data = self.json_storage.read(str(file_path))
    if isinstance(data, dict):
        return data.get("synopsis", "")
    return None
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile src/storage/manuscript_repository.py`
Expected: 无输出（成功）

- [ ] **Step 3: 提交**

```bash
git add src/storage/manuscript_repository.py
git commit -m "feat(storage): implement save_synopsis and load_synopsis"
```

---

## Task 3: 实现口播稿大纲相关方法

**Files:**
- Modify: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 添加 outline 相关方法**

```python
def save_outline(self, book_id: str, outline: dict) -> None:
    """保存口播稿大纲（结构化 JSON）"""
    self._write_json(self._outline_file(book_id), outline)

def load_outline(self, book_id: str) -> dict | None:
    """加载口播稿大纲"""
    file_path = self._outline_file(book_id)
    if not file_path.exists():
        return None
    return self.json_storage.read(str(file_path))
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile src/storage/manuscript_repository.py`
Expected: 无输出（成功）

- [ ] **Step 3: 提交**

```bash
git add src/storage/manuscript_repository.py
git commit -m "feat(storage): implement save_outline and load_outline"
```

---

## Task 4: 实现章节草稿相关方法

**Files:**
- Modify: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 添加 chapter_drafts 相关方法**

```python
def save_chapter_draft(self, book_id: str, chapter_id: str, draft: str) -> None:
    """保存单个章节草稿"""
    drafts = self.load_all_drafts(book_id)
    drafts[chapter_id] = draft
    self._write_json(self._drafts_file(book_id), drafts)

def load_chapter_draft(self, book_id: str, chapter_id: str) -> str | None:
    """加载单个章节草稿"""
    drafts = self.load_all_drafts(book_id)
    return drafts.get(chapter_id)

def save_all_drafts(self, book_id: str, drafts: dict[str, str]) -> None:
    """批量保存章节草稿"""
    self._write_json(self._drafts_file(book_id), drafts)

def load_all_drafts(self, book_id: str) -> dict[str, str]:
    """加载所有章节草稿"""
    file_path = self._drafts_file(book_id)
    if not file_path.exists():
        return {}
    data = self.json_storage.read(str(file_path))
    if isinstance(data, dict):
        return data
    return {}
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile src/storage/manuscript_repository.py`
Expected: 无输出（成功）

- [ ] **Step 3: 提交**

```bash
git add src/storage/manuscript_repository.py
git commit -m "feat(storage): implement chapter draft methods"
```

---

## Task 5: 实现最终口播稿相关方法

**Files:**
- Modify: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 添加 final_manuscript 相关方法**

```python
def save_final_manuscript(self, book_id: str, manuscript: str) -> None:
    """保存最终口播稿"""
    file_path = self._final_manuscript_file(book_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(manuscript, encoding="utf-8")

def load_final_manuscript(self, book_id: str) -> str | None:
    """加载最终口播稿"""
    file_path = self._final_manuscript_file(book_id)
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile src/storage/manuscript_repository.py`
Expected: 无输出（成功）

- [ ] **Step 3: 提交**

```bash
git add src/storage/manuscript_repository.py
git commit -m "feat(storage): implement final manuscript methods"
```

---

## Task 6: 实现工具方法

**Files:**
- Modify: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 添加 delete 和 exists 方法**

```python
def delete_manuscript(self, book_id: str) -> None:
    """删除口播稿相关所有文件"""
    files = [
        self._synopsis_file(book_id),
        self._outline_file(book_id),
        self._drafts_file(book_id),
        self._final_manuscript_file(book_id),
    ]
    for file_path in files:
        if file_path.exists():
            file_path.unlink()

def manuscript_exists(self, book_id: str) -> bool:
    """检查口播稿是否已生成（至少存在大纲文件）"""
    return self._outline_file(book_id).exists()
```

- [ ] **Step 2: 验证语法**

Run: `python -m py_compile src/storage/manuscript_repository.py`
Expected: 无输出（成功）

- [ ] **Step 3: 提交**

```bash
git add src/storage/manuscript_repository.py
git commit -m "feat(storage): implement utility methods"
```

---

## Task 7: 验证功能正确性

**Files:**
- Test: `src/storage/manuscript_repository.py`

- [ ] **Step 1: 验证导入**

Run: `python -c "from src.storage.manuscript_repository import ManuscriptRepository; print('OK')"`
Expected: OK

- [ ] **Step 2: 功能测试**

```python
from src.storage.manuscript_repository import ManuscriptRepository

repo = ManuscriptRepository()
book_id = "test-book-id"

# 测试保存和加载 synopsis
repo.save_synopsis(book_id, "测试故事梗概")
assert repo.load_synopsis(book_id) == "测试故事梗概"

# 测试保存和加载 outline
outline = {"story_synopsis": "test", "manuscript_outline": []}
repo.save_outline(book_id, outline)
assert repo.load_outline(book_id) == outline

# 测试保存和加载章节草稿
repo.save_chapter_draft(book_id, "ch1", "第一章草稿")
assert repo.load_chapter_draft(book_id, "ch1") == "第一章草稿"

# 测试批量保存草稿
repo.save_all_drafts(book_id, {"ch2": "第二章草稿", "ch3": "第三章草稿"})
drafts = repo.load_all_drafts(book_id)
assert drafts["ch2"] == "第二章草稿"
assert drafts["ch3"] == "第三章草稿"

# 测试最终口播稿
repo.save_final_manuscript(book_id, "最终口播稿内容")
assert repo.load_final_manuscript(book_id) == "最终口播稿内容"

# 测试 manuscript_exists
assert repo.manuscript_exists(book_id) == True

# 测试删除
repo.delete_manuscript(book_id)
assert repo.load_synopsis(book_id) is None
assert repo.manuscript_exists(book_id) == False

print("All tests passed!")
```

- [ ] **Step 3: 清理测试数据**

```python
# 清理测试书籍数据
import shutil
from pathlib import Path
shutil.rmtree(Path("data/books/test-book-id"), ignore_errors=True)
```

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "test(storage): verify ManuscriptRepository functionality"
```

---

## 自检清单

- [ ] `save_synopsis` / `load_synopsis` 实现
- [ ] `save_outline` / `load_outline` 实现
- [ ] `save_chapter_draft` / `load_chapter_draft` / `save_all_drafts` / `load_all_drafts` 实现
- [ ] `save_final_manuscript` / `load_final_manuscript` 实现
- [ ] `delete_manuscript` / `manuscript_exists` 实现
- [ ] 语法验证通过
- [ ] 功能测试通过