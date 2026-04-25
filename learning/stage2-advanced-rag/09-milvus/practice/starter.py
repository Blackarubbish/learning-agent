"""
Milvus Lite CRUD 实操

学习目标：
1. 零配置启动 Milvus Lite（本地 SQLite 模式）
2. 跑通 创建集合 → 插入 → 查询 → 搜索 → 更新 → 删除 全流程
3. 对比 FAISS，理解向量数据库的优势

运行：
  uv run python starter.py
"""

import random
from pathlib import Path

from pymilvus import MilvusClient

# 清理旧数据，保证每次运行干净
DB_PATH = Path(__file__).parent / "milvus_demo.db"
if DB_PATH.exists():
    DB_PATH.unlink()


# ============================================================
# 1. 创建客户端 + 集合
# ============================================================
# TODO: 用 MilvusClient 创建本地客户端，传入 DB_PATH
client = MilvusClient(str(DB_PATH))

COLLECTION = "ai_articles"
DIMENSION = 768

# TODO: 创建集合，需要指定 collection_name 和 dimension
client.create_collection(collection_name=COLLECTION, dimension=DIMENSION)

# 验证：打印集合列表和集合信息
print(f"集合列表: {client.list_collections()}")


# ============================================================
# 2. 插入数据 (Create)
# ============================================================
def mock_vector(seed):
    """生成模拟向量（实际应用中用 Embedding 模型生成）"""
    random.seed(seed)
    return [random.gauss(0, 1) for _ in range(DIMENSION)]


articles = [
    {
        "id": 1,
        "vector": mock_vector(1),
        "text": "深度学习是机器学习的一个分支，使用多层神经网络。",
        "category": "AI基础",
        "year": 2023,
    },
    {
        "id": 2,
        "vector": mock_vector(2),
        "text": "GPT-4是OpenAI发布的大语言模型，具有强大的推理能力。",
        "category": "大模型",
        "year": 2024,
    },
    {
        "id": 3,
        "vector": mock_vector(3),
        "text": "Python在数据科学和机器学习中被广泛使用。",
        "category": "编程语言",
        "year": 2023,
    },
    {
        "id": 4,
        "vector": mock_vector(4),
        "text": "Transformer架构采用自注意力机制，是现代LLM的基础。",
        "category": "AI基础",
        "year": 2024,
    },
    {
        "id": 5,
        "vector": mock_vector(5),
        "text": "FAISS是Facebook开发的向量相似度搜索库。",
        "category": "向量检索",
        "year": 2023,
    },
    {
        "id": 6,
        "vector": mock_vector(6),
        "text": "Milvus是高性能开源向量数据库，支持十亿级向量。",
        "category": "向量检索",
        "year": 2024,
    },
    {
        "id": 7,
        "vector": mock_vector(7),
        "text": "RAG技术将信息检索与大语言模型结合，减少幻觉。",
        "category": "大模型",
        "year": 2024,
    },
    {
        "id": 8,
        "vector": mock_vector(8),
        "text": "CNN卷积神经网络在图像识别中表现出色。",
        "category": "AI基础",
        "year": 2022,
    },
    {
        "id": 9,
        "vector": mock_vector(9),
        "text": "Rust语言注重安全性和性能，适合系统编程。",
        "category": "编程语言",
        "year": 2023,
    },
    {
        "id": 10,
        "vector": mock_vector(10),
        "text": "HNSW是一种基于图的近似最近邻搜索算法。",
        "category": "向量检索",
        "year": 2024,
    },
]

# TODO: 插入 articles 数据
client.insert(collection_name=COLLECTION, data=articles)

print(f"插入 {len(articles)} 条数据")

# TODO: 增量插入一条新数据（id=11）
# 提示：这是 FAISS 做不到的——随时 insert，不用重建索引

client.insert(
    collection_name=COLLECTION,
    data=[
        {
            "id": 11,
            "vector": mock_vector(10),
            "text": "ONE PLUS ONE EQUAL TWO",
            "category": "向量检索",
            "year": 2024,
        },
    ],
)

# ============================================================
# 3. 精准查询 (Read)
# ============================================================
# FAISS 的痛点：只支持向量检索，不支持按属性过滤
# Milvus 支持 SQL-like 的过滤表达式

# TODO: 按 ID 查询 id in [1, 2, 3]
by_id = client.query(collection_name=COLLECTION, filter="id in [1,2,3]", output_fields=["text"])

# TODO: 按属性查询 category == "向量检索"
by_category = client.query(
    collection_name=COLLECTION, filter='category == "向量检索"', output_fields=["text"]
)

# TODO: 组合条件查询 year >= 2024 and category == "AI基础"
by_combo = client.query(
    collection_name=COLLECTION,
    filter='year >= 2024 and category == "AI基础"',
    output_fields=["text"],
)

print(f"按ID查询: {len(by_id)} 条")
print(f"按分类查询: {len(by_category)} 条")
print(f"组合查询: {len(by_combo)} 条")


# ============================================================
# 4. 向量搜索 (Search)
# ============================================================
# 和 FAISS 的 similarity_search 类似，但 Milvus 支持更多参数

# TODO: 用 mock_vector(1) 的向量搜索 top-5
search_results = client.search(
    collection_name=COLLECTION, data=[mock_vector(1)], limit=5, output_fields=["text"]
)

print("向量搜索 top-5 完成")


# ============================================================
# 5. 更新数据 (Update)
# ============================================================
# Milvus 的 upsert：存在则更新，不存在则插入

# 查看更新前
before = client.query(
    collection_name=COLLECTION, filter="id == 1", output_fields=["id", "text", "year"]
)
print(f"更新前 year={before[0]['year']}")

# TODO: upsert 更新 id=1 的数据，把 year 改为 2024
client.upsert(
    collection_name=COLLECTION,
    data=[
        {
            "id": 1,
            "vector": mock_vector(1),
            "text": "深度学习是机器学习的一个分支，使用多层神经网络。",
            "category": "AI基础",
            "year": 2024,
        },
    ],
)

# 验证更新
after = client.query(
    collection_name=COLLECTION, filter="id == 1", output_fields=["id", "text", "year"]
)
print(f"更新后 year={after[0]['year']}")


# ============================================================
# 6. 删除数据 (Delete)
# ============================================================

# TODO: 按 ID 删除 id == 11
client.delete(collection_name=COLLECTION, filter="id == 11")

# TODO: 按条件批量删除 category == "编程语言"

client.delete(collection_name=COLLECTION, filter='category == "编程语言"')

# 验证删除
remaining = client.query(
    collection_name=COLLECTION, filter='category == "编程语言"', output_fields=["id"]
)
print(f"删除后 剩余编程语言: {len(remaining)} 条")


# ============================================================
# 自检


# ============================================================
if __name__ == "__main__":
    # 验证基本功能
    assert len(by_id) == 3, f"按ID查询应有3条，实际{len(by_id)}"
    assert len(by_category) == 4, f"向量检索分类应有3条，实际{len(by_category)}"
    assert len(by_combo) == 1, f"组合查询应有1条，实际{len(by_combo)}"
    assert after[0]["year"] == 2024, f"更新后year应为2024，实际{after[0]['year']}"
    assert len(remaining) == 0, f"删除后应无编程语言数据，实际{len(remaining)}"

    print("\n✅ 所有自检通过！")

    # 清理
    client.drop_collection(COLLECTION)
    print("已清理集合")
