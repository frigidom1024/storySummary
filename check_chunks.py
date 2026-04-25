# 查看pipeline的chunk结果
import os
import sys
import pathlib
from src.utils.reader.text import AdaptiveChunker
from src.utils.reader import read_book

# 设置项目根目录
project_root = "d:\project\storySummary"
os.chdir(project_root)

# 确保输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# 要处理的书籍路径
book_path = pathlib.Path("samples") / "局外人.epub"

print(f"文件是否存在: {book_path.exists()}")
print(f"文件路径: {book_path.absolute()}")

# 使用reader读取书籍
reader = read_book(book_path)
print(f"书籍标题: {reader.title}")

# 使用AdaptiveChunker进行分块
print("\n开始分块...")
chunker = AdaptiveChunker()
chunks = chunker.chunk(reader.read())
print(f"生成了 {len(chunks)} 个chunk")

# 查看每个chunk的内容
print("\n详细chunk信息:")
for i, chunk in enumerate(chunks):
    print(f"\n=== Chunk {i+1} ===")
    print(f"章节: {chunk.chapter or '无章节'}")
    print(f"ID: {chunk.id or '无ID'}")
    print(f"内容长度: {len(chunk.text)} 字符")
    # 尝试安全地显示内容预览
    try:
        preview = chunk.text[:200]
        print(f"内容预览: {preview}...")  # 只显示前200个字符
    except Exception as e:
        print(f"内容预览: [无法显示，错误: {e}]")
