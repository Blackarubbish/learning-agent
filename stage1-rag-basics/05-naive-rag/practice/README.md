# Naive RAG 实战项目：文档问答 API

## 项目目标

构建一个完整的端到端文档问答系统，支持：
- **文档上传摄取**：用户上传自己的文档（txt/pdf），系统自动向量化存储
- **基于文档问答**：用户根据已摄取的文档内容进行问答

## 项目结构

```
practice/
├── main.py              # 主程序
├── requirements.txt    # 依赖
└── data/
    └── sample.txt      # 示例文档（可选）
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
uvicorn main:app --reload --port 8000
```

访问 API 文档：http://localhost:8000/docs

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /ingest` | 上传文件 | 上传文档并摄取，返回 session_id |
| `POST /ask` | 问答 | 根据 session_id 和问题返回答案 |
| `GET /sessions` | 列表 | 查看已摄取的文档 sessions |
| `GET /health` | 健康检查 | 服务状态 |

## 使用流程

### 1. 上传文档

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@your_document.txt"
```

返回：
```json
{
  "session_id": "a1b2c3d4",
  "filename": "your_document.txt",
  "chunks": 15,
  "message": "文档摄取成功，可以开始问答了"
}
```

### 2. 问答

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"session_id": "a1b2c3d4", "question": "文档主要内容是什么？"}'
```

返回：
```json
{
  "answer": "这篇文档讲述了...",
  "sources": [
    "文档第一段内容...",
    "文档第二段内容..."
  ]
}
```

### 3. 查看所有 sessions

```bash
curl http://localhost:8000/sessions
```

## 支持的文件格式

- `.txt` 纯文本文件
- `.pdf` PDF 文档

## 实践任务

### 任务 1：完整流程测试
1. 启动服务
2. 上传一个 txt 文件
3. 根据文档内容提问
4. 检查返回的参考文档

### 任务 2：上传 PDF
1. 准备一个 PDF 文件
2. 上传并摄取
3. 基于 PDF 内容问答

### 任务 3：多文档测试
1. 上传多个不同主题的文档
2. 分别用不同 session_id 问答
3. 观察不同文档的问答效果

### 任务 4（挑战）：添加 Word 文档支持
- 安装 `langchain-community` 的 Word 加载器
- 支持 `.docx` 文件上传