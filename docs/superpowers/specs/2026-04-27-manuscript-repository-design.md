# ManuscriptRepository 口播稿仓储设计

## 目标

创建 `ManuscriptRepository` 类，提供口播稿工作流成果的存储和访问接口。

## 存储结构

复用 `data/books/{book_id}/` 目录：

```
data/books/{book_id}/
├── synopsis.json        # 故事梗概
├── outline.json        # 口播稿大纲（结构化 JSON）
├── chapter_drafts.json # 各章节草稿 {chapter_id: draft_text}
└── final_manuscript.txt # 最终口播稿
```

## 接口设计

```python
class ManuscriptRepository:
    """口播稿仓储 - 管理口播稿工作流成果的存储"""

    # === 故事梗概 ===

    def save_synopsis(self, book_id: str, synopsis: str) -> None:
        """保存故事梗概"""

    def load_synopsis(self, book_id: str) -> str | None:
        """加载故事梗概"""

    # === 口播稿大纲 ===

    def save_outline(self, book_id: str, outline: dict) -> None:
        """保存口播稿大纲（结构化 JSON）"""

    def load_outline(self, book_id: str) -> dict | None:
        """加载口播稿大纲"""

    # === 章节草稿 ===

    def save_chapter_draft(self, book_id: str, chapter_id: str, draft: str) -> None:
        """保存单个章节草稿"""

    def load_chapter_draft(self, book_id: str, chapter_id: str) -> str | None:
        """加载单个章节草稿"""

    def save_all_drafts(self, book_id: str, drafts: dict[str, str]) -> None:
        """批量保存章节草稿"""

    def load_all_drafts(self, book_id: str) -> dict[str, str]:
        """加载所有章节草稿"""

    # === 最终口播稿 ===

    def save_final_manuscript(self, book_id: str, manuscript: str) -> None:
        """保存最终口播稿"""

    def load_final_manuscript(self, book_id: str) -> str | None:
        """加载最终口播稿"""

    # === 工具方法 ===

    def delete_manuscript(self, book_id: str) -> None:
        """删除口播稿相关所有文件"""

    def manuscript_exists(self, book_id: str) -> bool:
        """检查口播稿是否已生成"""
```

## 文件格式

### synopsis.json
```json
{
  "synopsis": "故事梗概内容..."
}
```

### outline.json
```json
{
  "story_synopsis": "...",
  "manuscript_outline": [...],
  "metadata": {...}
}
```

### chapter_drafts.json
```json
{
  "chapter_1_id": "第一章草稿内容...",
  "chapter_2_id": "第二章草稿内容..."
}
```

### final_manuscript.txt
纯文本文件

## 实现要点

- 复用 `BookRepository._book_dir(book_id)` 获取书籍目录
- 使用 `JsonStorage` 读写 JSON 文件
- 原子写入保证数据安全
- 返回 `None` 表示文件不存在