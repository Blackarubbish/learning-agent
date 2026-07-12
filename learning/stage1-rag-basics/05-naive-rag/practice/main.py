"""
Naive RAG 实战：端到端文档问答系统
功能：
  - 文档上传与摄取
  - 基于用户文档的问答

运行：
  uvicorn main:app --reload --port 8000
"""

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from zai import ZhipuAiClient
import pdfplumber


class ZhipuEmbeddings(Embeddings):
    """智谱AI Embeddings包装器"""

    def __init__(self, client):
        self.client = client

    def embed_documents(self, texts):
        response = self.client.embeddings.create(model="embedding-3", input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text):
        response = self.client.embeddings.create(model="embedding-3", input=[text])
        return response.data[0].embedding


deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
zhipu_api_key = os.getenv("ZHIPU_API_KEY")

if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY environment variable not set")
if not zhipu_api_key:
    raise ValueError("ZHIPU_API_KEY environment variable not set")

zhipu_client = ZhipuAiClient(api_key=zhipu_api_key)
embeddings = ZhipuEmbeddings(zhipu_client)

app = FastAPI(title="Naive RAG API", version="1.0.0")

UPLOAD_DIR = Path("uploads")
INDEX_DIR = Path("indices")
INDEX_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

session_vectorstores: dict[str, FAISS] = {}
session_chains: dict[str, RunnablePassthrough] = {}


class QuestionRequest(BaseModel):
    session_id: str
    question: str


class QuestionResponse(BaseModel):
    answer: str
    sources: list[str]


class IngestResponse(BaseModel):
    session_id: str
    filename: str
    chunks: int
    message: str


class PDFLoader:
    """基于 pdfplumber 的 PDF 加载器"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list:
        from langchain_core.documents import Document

        docs = []
        with pdfplumber.open(self.file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    docs.append(
                        Document(
                            page_content=text, metadata={"page": i + 1, "source": self.file_path}
                        )
                    )
        return docs


def get_loader(file_path: str, file_ext: str):
    """根据文件类型获取加载器"""
    if file_ext == ".txt":
        return TextLoader(file_path, encoding="utf-8")
    elif file_ext == ".pdf":
        return PDFLoader(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")


def ingest_document(session_id: str, file_path: str, filename: str) -> IngestResponse:
    """摄取文档"""
    file_ext = Path(filename).suffix.lower()

    try:
        loader = get_loader(file_path, file_ext)
        docs = loader.load()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文档加载失败: {str(e)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50, separators=["\n\n", "\n", "。", "？", "！", " ", ""]
    )
    chunks = splitter.split_documents(docs)

    vectorstore = FAISS.from_documents(chunks, embeddings)

    index_path = INDEX_DIR / session_id
    vectorstore.save_local(str(index_path))

    session_vectorstores[session_id] = vectorstore
    session_chains.pop(session_id, None)

    return IngestResponse(
        session_id=session_id,
        filename=filename,
        chunks=len(chunks),
        message="文档摄取成功，可以开始问答了",
    )


RAG_PROMPT = PromptTemplate.from_template(
    '你是一个问答助手。请根据以下参考资料回答用户问题，保持简洁。如果无法找到答案，请说"我不知道"。\n\n'
    "参考资料：\n"
    "{context}\n\n"
    "问题：{question}\n\n"
    "回答："
)


def get_chain(session_id: str) -> RunnablePassthrough:
    """获取或创建问答 Chain"""
    if session_id in session_chains:
        return session_chains[session_id]

    if session_id not in session_vectorstores:
        index_path = INDEX_DIR / session_id
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="该 session 未找到，请先上传文档")
        vectorstore = FAISS.load_local(str(index_path), embeddings)
        session_vectorstores[session_id] = vectorstore

    vectorstore = session_vectorstores[session_id]
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}, return_source_documents=True)
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0,
        openai_api_key=deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )

    session_chains[session_id] = chain
    return chain


@app.post("/ingest", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)):
    """上传并摄取文档"""
    session_id = str(uuid.uuid4())[:8]

    file_path = UPLOAD_DIR / f"{session_id}_{file.filename}"
    with file_path.open("wb") as f:
        content = await file.read()
        f.write(content)

    try:
        result = ingest_document(session_id, str(file_path), file.filename)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"摄取失败: {str(e)}")


@app.post("/ask", response_model=QuestionResponse)
def ask_question(req: QuestionRequest):
    """问答接口"""
    try:
        chain = get_chain(req.session_id)
    except HTTPException as e:
        raise e

    answer = chain.invoke(req.question)

    vectorstore = session_vectorstores.get(req.session_id)
    docs = []
    if vectorstore:
        docs = vectorstore.similarity_search(req.question, k=3)

    return QuestionResponse(answer=answer, sources=[doc.page_content for doc in docs])


@app.get("/health")
def health():
    return {"status": "ok", "message": "Naive RAG API Running"}


@app.get("/sessions")
def list_sessions():
    """列出已摄取的文档 sessions"""
    sessions = []
    for session_id in session_vectorstores.keys():
        sessions.append({"session_id": session_id})
    for idx_path in INDEX_DIR.iterdir():
        if idx_path.is_dir() and idx_path.name not in session_vectorstores:
            sessions.append({"session_id": idx_path.name})
    return {"sessions": sessions}


if __name__ == "__main__":
    print("启动 Naive RAG API: http://localhost:8000")
    print("API 文档: http://localhost:8000/docs")
