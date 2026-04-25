"""
高级数据处理实操

学习目标：
1. 对比"朴素加载"和"结构化解析"的差异
2. 用 Unstructured 按元素类型分类（标题/正文/表格）
3. 实现文本清洗
4. 理解文档解析对 RAG 分块质量的影响

运行：
  uv run python starter.py
"""

import re
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from unstructured.partition.html import partition_html

HTML_FILE = Path(__file__).parent / "sample_report.html"


# ============================================================
# 1. 朴素加载：直接读 HTML 文本
# ============================================================
# 这就是之前 TextLoader 做的事——把文件当纯文本读进来

print("=" * 60)
print("1. 朴素加载")
print("=" * 60)

# TODO: 读取 HTML_FILE 的全部文本
loader = TextLoader(file_path=str(HTML_FILE))
naive_text = loader.load()
print(f"朴素加载: {len(naive_text)} 字符")
print(f"前 200 字: {naive_text[:200]}...")


# ============================================================
# 2. 结构化解析：用 Unstructured
# ============================================================
# Unstructured 能"看懂"文档结构：区分标题、正文、表格等


print(f"\n{'=' * 60}")
print("2. 结构化解析 (Unstructured)")
print(f"{'=' * 60}")

# TODO: 用 partition_html 解析 HTML_FILE
elements = partition_html(filename=str(HTML_FILE))

# TODO: 打印每个元素的类型和内容（前 50 字符）
# 提示：el.category 获取类型，el.text 获取文本
for i, el in enumerate(elements, 1):
    text_preview = el.text[:50] + "..." if len(el.text) > 50 else el.text
    print(f"{i}. 类型: {el.category}")
    print(f"   内容: {text_preview}")
    print()


# ============================================================
# 3. 按元素类型分类
# ============================================================
# 这是"文档解析"vs"文档加载"的核心区别：
# 解析能告诉你"这段文本是什么"（标题？正文？表格？）

print(f"\n{'=' * 60}")
print("3. 按元素类型分类")
print(f"{'=' * 60}")

# TODO: 把 elements 按 category 分成三组
titles = [
    el for el in elements if el.category in ["Title", "HeaderText"]
]  # category == "Title" 或 "HeaderText"
texts = [
    el for el in elements if el.category in ["NarrativeText", "ListItem", "UncategorizedText"]
]  # category == "NarrativeText" 或 "ListItem"
tables = [el for el in elements if el.category == "Table"]  # category == "Table"

print(f"标题: {len(titles)} 个")
print(f"正文: {len(texts)} 个")
print(f"表格: {len(tables)} 个")

# 打印表格内容——看看 Unstructured 是怎么识别表格结构的
for i, t in enumerate(tables):
    print(f"\n--- 表格 {i + 1} ---")
    print(t.text[:200] if len(t.text) > 200 else t.text)


# ============================================================
# 4. 文本清洗
# ============================================================
# 从 HTML 提取的文本可能有多余空白、特殊字符等

print(f"\n{'=' * 60}")
print("4. 文本清洗")
print(f"{'=' * 60}")


def clean_text(text: str) -> str:
    """清洗文本：移除多余空白，保留有意义的内容"""
    # TODO: 实现 3 个清洗步骤
    # 1. 移除多余空白（多个空格/换行合并为一个空格）
    cleaned = re.sub(r"\s+", " ", text)
    # 2. 移除特殊字符（保留中文、英文、数字、常用标点）
    cleaned = re.sub(
        r"[^\u4e00-\u9fffa-zA-Z0-9\s.,!?;:()\[\]{}\'\"\-。，！？；：" "''「」『』（）【】《》]",
        "",
        cleaned,
    )
    # 3. 去除首尾空白
    cleaned = cleaned.strip()
    return cleaned


# 对正文元素做清洗
cleaned_texts = [clean_text(t.text) for t in texts]
print(f"清洗前 (第1个正文): '{texts[0].text[:80]}'")
print(f"清洗后 (第1个正文): '{cleaned_texts[0][:80]}'")


# ============================================================
# 5. 对比两种方式的分块效果
# ============================================================
# 关键问题：如果表格被混进文本再分块，会发生什么？

splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

# 方式 A：朴素分块（所有文本混在一起）
print(f"\n{'=' * 60}")
print("5. 分块对比")
print(f"{'=' * 60}")

# TODO: 把所有元素的文本拼在一起，用 splitter 分块
all_text = [t.page_content for t in naive_text]
naive_chunks = splitter.split_text("\n".join(all_text))
print(f"\n方式A (朴素): {len(naive_chunks)} 个 chunks")

# 看看表格是否被截断了
for i, chunk in enumerate(naive_chunks):
    if "GPT-4o" in chunk or "FAISS" in chunk:
        print(f"  chunk[{i}]: {chunk[:100]}...")

# 方式 B：结构化分块（正文分块 + 表格独立保留）
# TODO: 正文用 splitter 分块，表格作为独立 chunk 保留
structured_text_chunks = [t.text for t in texts]  # 正文分块结果
table_chunks = [tb.text for tb in tables]  # 表格列表（每个表格一个 chunk）
structured_chunks = structured_text_chunks + table_chunks
print(
    f"\n方式B (结构化): {len(structured_chunks)} 个 chunks (正文 {len(structured_text_chunks)} + 表格 {len(table_chunks)})"
)

# 看看表格是否完整保留
for i, chunk in enumerate(structured_chunks):
    if "GPT-4o" in chunk or "FAISS" in chunk:
        print(f"  chunk[{i}]: {chunk[:100]}...")


# ============================================================
# 自检
# ============================================================
if __name__ == "__main__":
    assert naive_text is not None and len(naive_text) > 0, "朴素加载应读取到文本"
    assert len(elements) > 0, "Unstructured 应解析出元素"
    assert len(tables) >= 2, f"应识别出至少2个表格，实际{len(tables)}"
    assert len(naive_chunks) > 0, "朴素分块应产生chunks"
    assert len(table_chunks) >= 2, f"结构化分块应保留至少2个表格chunk，实际{len(table_chunks)}"

    # 关键断言：结构化分块中，表格 chunk 应包含完整表格头（<th> 标签对应的内容）
    table_chunk_text = " ".join(table_chunks)
    assert "模型" in table_chunk_text or "数据库" in table_chunk_text, "表格chunk应包含表头信息"

    print("\n✅ 所有自检通过！")
