# Milvus 向量数据库 (Day 12)

## 概述

Milvus 是高性能、可扩展的开源向量数据库，支持十亿级向量规模，专为生产环境设计。

## 核心优势

- ✅ 分布式架构，支持海量数据（10亿+ 向量）
- ✅ 多种索引算法（FLAT、IVF、HNSW、DiskANN）
- ✅ GPU 加速支持
- ✅ 云原生设计（K8s 友好）
- ✅ 混合检索（向量 + 属性过滤）

## 部署方式对比

| 方式 | 适用场景 | 复杂度 | 数据规模 |
|------|----------|--------|----------|
| **Milvus Lite** | 本地开发、笔记本 | ⭐ | 数十万 |
| **Milvus Standalone** | 单机部署、小规模生产 | ⭐⭐ | 百万级 |
| **Milvus Cluster** | 分布式生产环境 | ⭐⭐⭐⭐ | 十亿级 |

---

## 1. Milvus Lite（快速入门）

适合本地开发和小规模应用。

### 安装

```bash
pip install pymilvus
```

### 基本使用

```python
from pymilvus import MilvusClient

# 创建客户端（自动创建数据库文件）
client = MilvusClient("milvus_demo.db")

# 创建集合
client.create_collection(
    collection_name="demo_collection",
    dimension=768  # 向量维度
)

# 插入数据
client.insert(
    collection_name="demo_collection",
    data=[
        {"id": 1, "vector": [0.1] * 768, "text": "这是第一个文档"},
        {"id": 2, "vector": [0.2] * 768, "text": "这是第二个文档"},
    ]
)

# 搜索
results = client.search(
    collection_name="demo_collection",
    data=[[0.1] * 768],
    limit=5
)
print(results)
```

---

## 2. Docker 部署 Milvus Standalone

### 快速启动

```bash
# 下载安装脚本
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh

# 启动 Milvus
bash standalone_embed.sh start

# 检查状态
curl -s http://localhost:9091/health
```

### Docker Compose 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  milvus:
    image: milvusdb/milvus:latest
    container_name: milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - ./milvus_data:/milvus/data
    environment:
      - ETCD_ENDPOINTS=etcd:2379
      - MINIO_ADDRESS=minio:9000
    depends_on:
      - etcd
      - minio

  etcd:
    image: quay.io/coreos/etcd:latest
    container_name: milvus-etcd
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ./etcd_data:/etcd
    command: etcd -advertise-client-url-urls=http://127.0.0.1:2379 -listen-client-urls=http://0.0.0.0:2379 --data-dir=/etcd

  minio:
    image: minio/minio:latest
    container_name: milvus-minio
    environment:
      MINIO_ACCESS_KEY=minioadmin
      MINIO_SECRET_KEY=minioadmin
    volumes:
      - ./minio_data:/minio
    command: minio server /minio --console-address ":9001"
```

```bash
docker-compose up -d

# 检查状态
curl http://localhost:9091/health
```

---

## 3. Python SDK 高级使用

### 连接 Milvus 服务器

```python
from pymilvus import MilvusClient

# 连接到远程服务器
client = MilvusClient(uri="http://localhost:19530")

# 或使用 Zilliz Cloud（托管服务）
client = MilvusClient(uri="https://xxx.zillizcloud.com:443", token="your-api-key")
```

### 创建集合（带索引）

```python
# 创建集合
client.create_collection(
    collection_name="my_collection",
    dimension=768,
    primary_field="id",
    vector_field="vector",
    id_type="int"
)

# 创建索引（插入数据前创建索引）
client.create_index(
    collection_name="my_collection",
    index_params={
        "metric_type": "IP",  # 内积相似度
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128}
    },
    field_name="vector"
)

# 加载集合到内存
client.load_collection("my_collection")
```

### CRUD 操作

```python
# 插入数据
import random

vectors = [[random.random() for _ in range(768)] for _ in range(1000)]
data = [{"id": i, "vector": vectors[i], "text": f"文档 {i}"}
        for i in range(1000)]

client.insert(collection_name="my_collection", data=data)

# 精准查询
results = client.query(
    collection_name="my_collection",
    filter="id in [1, 2, 3]",
    output_fields=["id", "text"]
)

# 搜索
search_results = client.search(
    collection_name="my_collection",
    data=[vectors[0]],
    limit=10,
    search_params={"metric_type": "IP"},
    output_fields=["id", "text"]
)

# 删除数据
client.delete(
    collection_name="my_collection",
    filter="id in [1, 2, 3]"
)

# 删除集合
client.drop_collection(collection_name="my_collection")
```

### 混合搜索（带过滤）

```python
# 带属性过滤的搜索
results = client.search(
    collection_name="my_collection",
    data=[[0.1] * 768],
    filter="category == '技术' and year >= 2020",
    limit=10,
    search_params={
        "metric_type": "IP",
        "params": {"nprobe": 10}
    }
)
```

---

## 4. 从 FAISS 迁移到 Milvus

### 导出 FAISS 索引

```python
import numpy as np

# 加载 FAISS 索引
index = faiss.read_index("faiss_index/index.faiss")

# 获取向量和元数据
vectors = index.reconstruct_n(0, index.ntotal)
metadata = []  # 需要从原始数据源获取
```

### 导入 Milvus

```python
from pymilvus import MilvusClient

client = MilvusClient("milvus_migration.db")

# 创建集合
client.create_collection(
    collection_name="migrated_collection",
    dimension=vectors.shape[1]
)

# 创建索引
client.create_index(
    collection_name="migrated_collection",
    index_params={
        "metric_type": "L2",  # 或 IP
        "index_type": "HNSW",
        "params": {"M": 16, "efConstruction": 200}
    },
    field_name="vector"
)

# 插入数据
data = [
    {"id": i, "vector": vectors[i].tolist(), "text": metadata[i]}
    for i in range(len(vectors))
]
client.insert(collection_name="migrated_collection", data=data)

# 加载
client.load_collection("migrated_collection")
```

---

## 5. Attu - Milvus 可视化工具

Attu 是 Milvus 官方提供的可视化客户端：

```bash
# 安装
docker pull zilliz/attu:latest

# 运行
docker run -d \
  --name attu \
  -p 8000:3000 \
  -e MILVUS_URL=localhost:19530 \
  zilliz/attu:latest

# 访问 http://localhost:8000
```

---

## 6. 索引类型选择

| 索引类型 | 适用场景 | 特点 |
|----------|----------|------|
| **FLAT** | 小规模数据（<10000） | 精确搜索，速度慢 |
| **IVF_FLAT** | 中等规模 | 聚类加速，需调整 nlist |
| **IVF_PQ** | 大规模数据 | 压缩加速，精度略有下降 |
| **HNSW** | 需要快速响应 | 内存占用高，速度快 |
| **DiskANN** | 超大规模 | 磁盘存储，成本低 |

### 索引参数建议

```python
# 小规模（<100万向量）
index_params = {
    "metric_type": "IP",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 1024}
}

# 中等规模（100万-1000万）
index_params = {
    "metric_type": "IP",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}

# 大规模（>1000万）
index_params = {
    "metric_type": "IP",
    "index_type": "HNSW",
    "params": {"M": 32, "efConstruction": 400}
}
```

---

## 实践任务

1. 使用 Docker 部署 Milvus Standalone
2. 使用 Python SDK 进行 CRUD 操作
3. 将 Week 1 的 FAISS 索引迁移到 Milvus
4. 对比 FAISS 和 Milvus 的检索性能

---

## 参考资源

- [Milvus 官方文档](https://milvus.io/docs/install_standalone-docker.md)
- [Milvus Python SDK](https://github.com/milvus-io/milvus)
- [新手如何使用 Milvus(CSDN)](https://blog.csdn.net/qq_58286779/article/details/146413500)
- [Milvus 向量数据库入门(知乎)](https://zhuanlan.zhihu.com/p/565254258)