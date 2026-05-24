# Stage 1: RAG 基础

## 01 FastAPI
### 核心概念
- 声明式路由 @app.get/post
- Pydantic BaseModel 自动验证
- 自动生成 OpenAPI /docs
- 依赖注入 Depends
### 对比 Node.js
- Express 过程式 → FastAPI 声明式
- Zod 手动校验 → Pydantic 类型即校验
### 实践
- uvicorn 启动开发服务器
- POST/GET 路由 + 路径参数 + 查询参数

## 02 LangChain
### 核心价值
- 组件化 + Chain 组合
- 统一 LLM 调用接口
### 六大模块
- Model I/O: LLM调用 + Prompt管理
- Retrieval: 文档加载/分割/向量检索
- Chains: 组件串联执行 LCEL
- Agents: 模型决定调用什么工具
- Memory: 对话上下文存储
- Callbacks: 事件钩子
### 关键 API
- ChatPromptTemplate 模板化 prompt
- StrOutputParser 字符串输出解析
- LCEL pipe 操作符 |

## 03 文档加载与分割
### 文档加载
- TextLoader: 纯文本
- PDFPlumberLoader: PDF
- UnstructuredFileLoader: 通用格式
- WebBaseLoader: 网页
### Document 对象
- page_content: 文本内容
- metadata: 来源/页码等元信息
### 文本分割
- 为什么分割: LLM上下文窗口有限
- RecursiveCharacterTextSplitter: 递归按分隔符切分
- chunk_size: 每块大小 500-1000
- chunk_overlap: 重叠 50-100 保语义连贯

## 04 向量化与存储
### Embedding
- 文本→数字向量的翻译器
- 语义相似的文字向量距离近
- embed_query: 单文本向量化
- embed_documents: 批量向量化
### VectorStore 对比
- FAISS: 本地内存, 小规模/demo
- Chroma: 专为LLM设计, 原型开发
- Milvus: 生产级分布式, 大规模数据
### FAISS 使用
- from_documents: 从文档创建向量库
- similarity_search: 语义相似度检索
- save_local/load_local: 持久化

## 05 Naive RAG 实战
### 端到端文档问答 API
- 上传文档 → 向量化存储 → 基于文档问答
### API 接口
- POST /ingest: 上传文档摄取
- POST /ask: 根据session_id问答
- GET /sessions: 查看已摄取文档
- GET /health: 健康检查
### 完整 Pipeline
- 加载→分割→Embedding→FAISS存储
- 提问→向量检索→获取相关文档→LLM生成
### 技术栈整合
- FastAPI + LangChain + FAISS + LLM
