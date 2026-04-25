# 09 - Milvus 向量数据库

## 目标
用 Milvus Lite 跑通 CRUD 全流程，理解向量数据库 vs 向量索引的本质区别。

## 前置知识
- FAISS 向量索引（04 章）
- Embedding 向量化（04 章）

## 运行方式
```bash
# 先安装依赖
uv add "pymilvus[milvus_lite]"

# 运行
uv run python starter.py
```

## 任务清单
1. 创建 MilvusClient + Collection
2. 插入带元数据的文档向量
3. 精准查询（按 ID / 按属性过滤）
4. 向量搜索（similarity search）
5. 更新数据（upsert）
6. 删除数据（按 ID / 按条件）
