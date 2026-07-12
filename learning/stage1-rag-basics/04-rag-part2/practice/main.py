from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from zai import ZhipuAiClient
import os


class ZhipuEmbeddings(Embeddings):
    """智谱AI Embeddings包装器"""

    def __init__(self, client):
        self.client = client

    def embed_documents(self, texts):
        """嵌入多个文档"""
        response = self.client.embeddings.create(model="embedding-3", input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text):
        """嵌入单个查询"""
        response = self.client.embeddings.create(model="embedding-3", input=[text])
        return response.data[0].embedding


zhipu_api_key = os.getenv("ZHIPU_API_KEY")
if not zhipu_api_key:
    raise ValueError("ZHIPU_API_KEY environment variable not set")

client = ZhipuAiClient(api_key=zhipu_api_key)
embeddings = ZhipuEmbeddings(client)


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


def vectorize_documents(chunks):
    """向量化文档"""
    print(f"开始向量化 {len(chunks)} 个文档块")

    vector_store = FAISS.from_documents(documents=chunks, embedding=embeddings)

    print(f"✅ 向量化完成：{len(chunks)} 个文档块")
    return vector_store


def similarity_search(vector_store, query, k=3):
    """相似度搜索"""
    results = vector_store.similarity_search(query, k=k)
    print(f"✅ 搜索完成：找到 {len(results)} 个相关文档")
    return results


if __name__ == "__main__":
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(script_dir, "sample.txt")

    print("📄 创建示例文档完成")

    docs = load_document(sample_path)

    chunks = split_documents(docs, chunk_size=500, chunk_overlap=50)
    print(f"✅ 分割完成：{len(chunks)} 个文档块")

    vector_store = vectorize_documents(chunks)

    save_path = os.path.join(script_dir, "faiss_index")
    vector_store.save_local(save_path)
    print(f"💾 已保存到: {save_path}")

    query = "数据管道负责收集"
    results = similarity_search(vector_store, query)

    print("\n🔍 搜索结果：")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.page_content}")
