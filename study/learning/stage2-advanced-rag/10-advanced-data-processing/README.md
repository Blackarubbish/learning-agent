# 高级数据处理 (Day 13)

## 概述

复杂文档（PDF、Word、HTML）包含表格、图片、布局等信息，需要专门的处理工具来提取。

## 核心工具对比

| 工具 | 擅长处理 | 特点 |
|------|----------|------|
| **Unstructured.io** | 通用文档 | 简单易用，支持多种格式 |
| **MinerU** | 复杂 PDF | 国产开源，高精度表格/图片 |
| **Docling** | 学术论文 | 布局感知，公式识别 |
| **PDF-Extract-Kit** | 中文 PDF | 专用中文文档提取 |

---

## 1. Unstructured.io

### 安装

```bash
# 基础安装
pip install unstructured

# 支持多种格式
pip install "unstructured[pdf]"
pip install "unstructured[docx]"
pip install "unstructured[html]"
```

### 基本使用

```python
from unstructured.partition.auto import partition

# 自动检测格式并解析
documents = partition(filename="example.pdf")

for doc in documents:
    print(f"Type: {doc.category}")
    print(f"Content: {doc.text}")
    print(f"Metadata: {doc.metadata}")
```

### LangChain 集成

```python
from langchain_community.document_loaders import UnstructuredFileLoader

# 加载 PDF
loader = UnstructuredFileLoader("example.pdf", mode="elements")
docs = loader.load()

# mode 可选: "single", "elements", "paged"
```

### 处理不同格式

```python
# 文本文件
from unstructured.partition.text import partition_text

text_docs = partition_text(filename="example.txt")

# Word 文档
from unstructured.partition.docx import partition_docx

docx_docs = partition_docx(filename="example.docx")

# HTML
from unstructured.partition.html import partition_html

html_docs = partition_html(filename="example.html")

# Markdown
from unstructured.partition.md import partition_md

md_docs = partition_md(filename="example.md")
```

### 处理表格

```python
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import elements_to_json

# 提取表格（需要安装 pdf 插件）
elements = partition_pdf(
    filename="table_example.pdf",
    infer_table_structure=True,  # 识别表格结构
)

# 提取表格元素
tables = [el for el in elements if el.category == "Table"]

for table in tables:
    print(f"Table text: {table.text}")
    print(f"HTML: {table.metadata.text_as_html}")
```

---

## 2. MinerU

国产开源的高精度文档解析工具，特别擅长处理中文 PDF。

### 安装

```bash
pip install magic-pdf
```

### 基本使用

```python
from magic_pdf.data.data_reader_writer import ReaderWriter
from magic_pdf.model.VBuild import VBuild
from magic_pdf.model.PredictCtrl import PredictController

# 初始化
pdf_path = "example.pdf"
content = ReaderWriter.read_pdf(pdf_path)

# 解析
result = VBuild.run(content)

# 获取结果
for item in result:
    print(f"Type: {item['type']}")
    print(f"Content: {item['content']}")
```

### 表格识别

```python
from magic_pdf.ops.table_ocr import table_ocr

# 识别表格
tables = table_ocr(image, ocr_model)
```

---

## 3. Docling

适合学术论文和技术文档。

### 安装

```bash
pip install docling
```

### 基本使用

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()

# 转换 PDF
result = converter.convert("paper.pdf")

# 获取文本
for element in result.document.body:
    print(element.text)

# 导出为 Markdown
result.export_to_markdown("output.md")
```

---

## 4. 完整 RAG 数据处理流程

```python
from unstructured.partition.auto import partition
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Milvus
from langchain_openai import OpenAIEmbeddings

class DocumentProcessor:
    def __init__(self, chunk_size=500, chunk_overlap=50):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " "]
        )

    def process_pdf(self, file_path, extract_tables=True):
        """处理 PDF 文件"""
        # 1. 解析文档
        elements = partition(
            filename=file_path,
            infer_table_structure=extract_tables,
            extract_images=False  # 图片暂不处理
        )

        # 2. 分类元素
        texts = []
        tables = []

        for el in elements:
            if el.category == "Table":
                tables.append(el.text)
            else:
                texts.append(el.text)

        # 3. 分割文本
        chunks = self.splitter.split_text("\n\n".join(texts))

        # 4. 添加表格（作为独立 chunk）
        chunks.extend(tables)

        return chunks

    def process_docx(self, file_path):
        """处理 Word 文档"""
        from unstructured.partition.docx import partition_docx

        elements = partition_docx(filename=file_path)
        texts = [el.text for el in elements if el.category not in ["Table", "Image"]]

        chunks = self.splitter.split_text("\n\n".join(texts))
        return chunks

    def process_html(self, file_path):
        """处理 HTML 文件"""
        from unstructured.partition.html import partition_html

        elements = partition_html(filename=file_path)
        texts = [el.text for el in elements]

        chunks = self.splitter.split_text("\n\n".join(texts))
        return chunks

# 使用示例
processor = DocumentProcessor()

# 处理多种格式
for file_path in ["doc1.pdf", "doc2.docx", "doc3.html"]:
    chunks = processor.process_pdf(file_path) if file_path.endswith(".pdf") \
        else processor.process_docx(file_path) if file_path.endswith(".docx") \
        else processor.process_html(file_path)

    # 存储到向量数据库
    for chunk in chunks:
        # ... 存储逻辑
```

---

## 5. 文本清洗最佳实践

```python
import re


def clean_text(text):
    """清洗文本"""
    # 移除多余空白
    text = re.sub(r"\s+", " ", text)

    # 移除特殊字符（保留中文、英文、数字、常用标点）
    text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:。，！？；：""' "（）()、]", "", text)

    # 移除开头结尾空白
    text = text.strip()

    return text


def extract_metadata(element):
    """提取元素元数据"""
    return {
        "category": element.category,
        "page_number": element.metadata.page_number,
        "coordinates": element.metadata.coordinates,
        "filename": element.metadata.filename,
    }
```

---

## 6. 处理复杂 PDF 示例

```python
from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import convert_to_dict

# 提取并保留布局信息
elements = partition_pdf(
    filename="complex.pdf",
    infer_table_structure=True,
    extract_images=True,
    extract_element_types=["table", "image", "title", "text"],
)

# 转换格式便于后续处理
element_dicts = convert_to_dict(elements)

# 按类型分组
grouped = {"titles": [], "texts": [], "tables": [], "images": []}

for el in element_dicts:
    cat = el["type"].lower()
    if "title" in cat:
        grouped["titles"].append(el)
    elif "table" in cat:
        grouped["tables"].append(el)
    elif "image" in cat:
        grouped["images"].append(el)
    else:
        grouped["texts"].append(el)

# 处理标题层级
for title in grouped["titles"]:
    level = title.get("metadata", {}).get("level", 1)
    print(f"{'#' * level} {title['text']}")
```

---

## 实践任务

1. 使用 Unstructured 解析 PDF 文档
2. 处理包含表格的复杂文档
3. 实现文本清洗流程
4. 集成到 RAG pipeline

---

## 参考资源

- [Unstructured.io GitHub](https://github.com/unstructured-io/unstructured)
- [Unstructured 库实战(CSDN)](https://blog.csdn.net/weixin_29062865/article/details/157824929)
- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [Docling GitHub](https://github.com/DS4SD/docling)