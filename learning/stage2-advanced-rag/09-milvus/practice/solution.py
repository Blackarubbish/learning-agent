"""
Milvus Lite CRUD 完整参考实现

学习目标：
1. 零配置启动 Milvus Lite（本地 SQLite 模式）
2. 跑通 创建集合 → 插入 → 查询 → 搜索 → 更新 → 删除 全流程
3. 对比 FAISS，理解向量数据库的优势

运行：
  uv run python solution.py
"""

import random
from pathlib import Path

# 清理旧数据，保证每次运行干净
DB_PATH = Path(__file__).parent / "milvus_demo.db"
if DB_PATH.exists():
    DB_PATH.unlink()

from pymilvus import MilvusClient


# ============================================================
# 1. 创建客户端 + 集合
# ============================================================
# Milvus Lite：传入本地 .db 文件路径即可，无需启动服务器
# str() 是必须的，MilvusClient 不接受 Path 对象
client = MilvusClient(str(DB_PATH))

COLLECTION = "ai_articles"
DIMENSION = 768

# create_collection 自动创建 id (主键) + vector 字段
# 数据会自动持久化到磁盘（FAISS 需要手动 write_index）
client.create_collection(collection_name=COLLECTION, dimension=DIMENSION)

print(f"集合列表: {client.list_collections()}")


# ============================================================
# 2. 插入数据 (Create)
# ============================================================
def mock_vector(seed):
    """生成模拟向量（实际应用中用 Embedding 模型生成）"""
    random.seed(seed)
    return [random.gauss(0, 1) for _ in range(DIMENSION)]


articles = [
    {"id": 1, "vector": mock_vector(1), "text": "深度学习是机器学习的一个分支，使用多层神经网络。", "category": "AI基础", "year": 2023},
    {"id": 2, "vector": mock_vector(2), "text": "GPT-4是OpenAI发布的大语言模型，具有强大的推理能力。", "category": "大模型", "year": 2024},
    {"id": 3, "vector": mock_vector(3), "text": "Python在数据科学和机器学习中被广泛使用。", "category": "编程语言", "year": 2023},
    {"id": 4, "vector": mock_vector(4), "text": "Transformer架构采用自注意力机制，是现代LLM的基础。", "category": "AI基础", "year": 2024},
    {"id": 5, "vector": mock_vector(5), "text": "FAISS是Facebook开发的向量相似度搜索库。", "category": "向量检索", "year": 2023},
    {"id": 6, "vector": mock_vector(6), "text": "Milvus是高性能开源向量数据库，支持十亿级向量。", "category": "向量检索", "year": 2024},
    {"id": 7, "vector": mock_vector(7), "text": "RAG技术将信息检索与大语言模型结合，减少幻觉。", "category": "大模型", "year": 2024},
    {"id": 8, "vector": mock_vector(8), "text": "CNN卷积神经网络在图像识别中表现出色。", "category": "AI基础", "year": 2022},
    {"id": 9, "vector": mock_vector(9), "text": "Rust语言注重安全性和性能，适合系统编程。", "category": "编程语言", "year": 2023},
    {"id": 10, "vector": mock_vector(10), "text": "HNSW是一种基于图的近似最近邻搜索算法。", "category": "向量检索", "year": 2024},
]

client.insert(collection_name=COLLECTION, data=articles)
print(f"插入 {len(articles)} 条数据")

# 增量插入——FAISS 做不到：需要 insert 后重建索引
# Milvus 随时 insert，增量写入
client.insert(
    collection_name=COLLECTION,
    data=[
        {"id": 11, "vector": mock_vector(11), "text": "LangChain是构建LLM应用的开源框架。", "category": "大模型", "year": 2024},
    ],
)
print("增量插入 1 条 (id=11)")


# ============================================================
# 3. 精准查询 (Read)
# ============================================================
# FAISS 只支持向量检索，不支持按属性过滤
# Milvus 支持 SQL-like 的过滤表达式，这是"数据库"vs"索引"的核心区别

by_id = client.query(
    collection_name=COLLECTION,
    filter="id in [1, 2, 3]",
    output_fields=["id", "text", "category", "year"],
)
print(f"按ID查询: {len(by_id)} 条")

by_category = client.query(
    collection_name=COLLECTION,
    filter='category == "向量检索"',
    output_fields=["id", "text", "category"],
)
# 原始3条 + 增量插入的id=11 category也是"向量检索"，但id=11的category是"大模型"
# 所以只有原始3条：id=5,6,10
print(f"按分类查询: {len(by_category)} 条")

by_combo = client.query(
    collection_name=COLLECTION,
    filter='year >= 2024 and category == "AI基础"',
    output_fields=["id", "text", "year"],
)
# 只有 id=4 满足 year>=2024 AND category=="AI基础"
# id=1 此时 year 还是 2023（还没 upsert）
print(f"组合查询: {len(by_combo)} 条")


# ============================================================
# 4. 向量搜索 (Search)
# ============================================================
search_results = client.search(
    collection_name=COLLECTION,
    data=[mock_vector(1)],
    limit=5,
    output_fields=["id", "text", "category"],
)
print("向量搜索 top-5:")
for hit in search_results[0]:
    print(f"  id={hit['entity']['id']}, distance={hit['distance']:.4f}, text={hit['entity']['text'][:30]}...")


# ============================================================
# 5. 更新数据 (Update)
# ============================================================
# upsert = 存在则更新，不存在则插入
# FAISS 没有原生更新——必须删除旧数据 + 重建索引

before = client.query(collection_name=COLLECTION, filter="id == 1", output_fields=["id", "text", "year"])
print(f"更新前 year={before[0]['year']}")

client.upsert(
    collection_name=COLLECTION,
    data=[
        {"id": 1, "vector": mock_vector(1), "text": "深度学习是机器学习的一个分支，使用多层神经网络来学习数据表征。", "category": "AI基础", "year": 2024},
    ],
)

after = client.query(collection_name=COLLECTION, filter="id == 1", output_fields=["id", "text", "year"])
print(f"更新后 year={after[0]['year']}")


# ============================================================
# 6. 删除数据 (Delete)
# ============================================================
# FAISS 没有原生删除——必须重建索引
# Milvus 支持按 ID 或按条件删除

client.delete(collection_name=COLLECTION, filter="id == 11")
print("删除 id=11")

client.delete(collection_name=COLLECTION, filter='category == "编程语言"')
print("批量删除 category=='编程语言'")

remaining = client.query(collection_name=COLLECTION, filter='category == "编程语言"', output_fields=["id"])
print(f"删除后 剩余编程语言: {len(remaining)} 条")


# ============================================================
# 自检
# ============================================================
if __name__ == "__main__":
    assert len(by_id) == 3, f"按ID查询应有3条，实际{len(by_id)}"
    assert len(by_category) == 3, f"向量检索分类应有3条，实际{len(by_category)}"
    assert len(by_combo) == 1, f"组合查询应有1条，实际{len(by_combo)}"
    assert after[0]["year"] == 2024, f"更新后year应为2024，实际{after[0]['year']}"
    assert len(remaining) == 0, f"删除后应无编程语言数据，实际{len(remaining)}"

    print("\n✅ 所有自检通过！")

    client.drop_collection(COLLECTION)
    print("已清理集合")
