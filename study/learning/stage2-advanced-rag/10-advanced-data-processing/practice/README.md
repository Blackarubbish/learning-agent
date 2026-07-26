# 10 - 高级数据处理

## 目标
用 Unstructured 解析结构化文档，对比"朴素加载"和"结构化解析"的差异，理解文档解析对 RAG 质量的影响。

## 前置知识
- 文档加载与分割（03 章）
- FAISS / Milvus 向量存储（04 / 09 章）

## 运行方式
```bash
# 安装依赖
uv add "unstructured[html]"

# 运行
uv run python starter.py
```

## 任务清单
1. 创建含标题、正文、表格的 HTML 测试文件
2. 用朴素方式加载（直接读文本）vs 用 Unstructured 结构化解析
3. 按元素类型分类（标题 / 正文 / 表格）
4. 实现文本清洗
5. 对比两种方式的分块效果
