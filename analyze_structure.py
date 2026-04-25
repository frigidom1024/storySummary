# 分析文本的章节结构
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

print(f"文件是否存在: {os.path.exists(book_path)}")

# 使用reader读取书籍
reader = read_book(book_path)
print(f"书籍标题: {reader.title}")

# 获取文本
text = reader.read()
print(f"\n总文本长度: {len(text)} 字符")

# 分析文本中的章节标记
print("\n=== 分析章节标记 ===")

# 检测中文章节标记
chinese_chapter_pattern = r'第[0-9零一二三四五六七八九十百千万\d]+[章节部篇卷册]'
chinese_matches = re.findall(chinese_chapter_pattern, text)
print(f"中文章节标记数量: {len(chinese_matches)}")
if chinese_matches:
    print(f"中文章节标记示例: {chinese_matches[:10]}")

# 检测法文章节标记 (Chapter, Part等)
french_chapter_pattern = r'(?:Chapter|Part|Chapitre|Première|Deuxième|Troisième|Partie)'
french_matches = re.findall(french_chapter_pattern, text, re.IGNORECASE)
print(f"\n法文章节标记数量: {len(french_matches)}")
if french_matches:
    print(f"法文章节标记示例: {list(set(french_matches))[:10]}")

# 检测数字编号章节
number_pattern = r'^[0-9]+[\.、\.\s]'
lines = text.split('\n')
number_chapters = [l.strip() for l in lines if re.match(number_pattern, l.strip())]
print(f"\n数字编号章节数量: {len(number_chapters)}")
if number_chapters:
    print(f"数字编号章节示例: {number_chapters[:10]}")

# 查看前100行的内容
print("\n=== 前100行内容 ===")
lines = text.split('\n')
for i, line in enumerate(lines[:100]):
    if line.strip():
        print(f"{i+1}: {line[:100]}...")
