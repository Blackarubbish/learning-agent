"""
RAG Part 1 实践：文档加载与分割
运行：python main.py
"""

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path: str):
    """加载文档"""
    loader = TextLoader(file_path)
    docs = loader.load()
    print(f"✅ 加载完成：{len(docs)} 个文档")
    return docs


def split_documents(docs, chunk_size: int, chunk_overlap: int):
    """分割文档"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "？", "！", ""],
    )
    chunks = splitter.split_documents(docs)
    return chunks


def analyze_chunks(chunks):
    """分析分割结果"""
    print(f"\n📊 分割结果分析：共 {len(chunks)} 个 chunks\n")

    for i, chunk in enumerate(chunks):
        content = chunk.page_content
        metadata = chunk.metadata
        print(f"--- Chunk {i + 1} ---")
        print(f"长度: {len(content)} 字符")
        print(f"内容: {content[:100]}{'...' if len(content) > 100 else ''}")
        print(f"元数据: {metadata}")
        print()


def main():
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(script_dir, "sample.txt")

    # 1. 加载文档
    print("=" * 50)
    print("第一步：加载文档")
    print("=" * 50)
    docs = load_document(sample_path)

    # 2. 使用不同参数分割
    configs = [
        {"chunk_size": 200, "chunk_overlap": 20},
        {"chunk_size": 500, "chunk_overlap": 50},
        {"chunk_size": 1000, "chunk_overlap": 100},
    ]

    for config in configs:
        print("\n" + "=" * 50)
        print(
            f"第二步：分割文档 (chunk_size={config['chunk_size']}, "
            f"chunk_overlap={config['chunk_overlap']})"
        )
        print("=" * 50)
        chunks = split_documents(docs, **config)
        analyze_chunks(chunks)


if __name__ == "__main__":
    main()
