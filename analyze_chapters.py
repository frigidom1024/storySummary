# 详细分析文本中的章节标记
import os
import sys
import re
from src.utils.reader import read_book

# 设置项目根目录
project_root = "d:\\project\\storySummary"
os.chdir(project_root)

# 确保输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# 要处理的书籍路径
book_path = "samples/局外人.epub"

# 使用reader读取书籍
reader = read_book(book_path)
text = reader.read()

# 按段落分割
paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

print(f"总段落数: {len(paragraphs)}")

# 查找所有包含juwairendi的段落
print("\n=== 所有包含 juwairendi 的段落 ===")
juwairendi_paragraphs = []
for i, para in enumerate(paragraphs):
    if 'juwairendi' in para.lower():
        juwairendi_paragraphs.append((i, para[:100]))
        print(f"段落 {i}: {para[:100]}...")

print(f"\n共找到 {len(juwairendi_paragraphs)} 个包含 juwairendi 的段落")

# 查找所有以 ## 开头的段落
print("\n=== 所有以 ## 开头的段落 ===")
hash_paragraphs = []
for i, para in enumerate(paragraphs):
    if para.startswith('##'):
        hash_paragraphs.append((i, para[:100]))
        print(f"段落 {i}: {para[:100]}...")

print(f"\n共找到 {len(hash_paragraphs)} 个以 ## 开头的段落")

# 检查每个大段落的长度
print("\n=== 超过10000字符的段落 ===")
for i, para in enumerate(paragraphs):
    if len(para) > 10000:
        print(f"段落 {i}: 长度 {len(para)}, 内容预览: {para[:100]}...")
