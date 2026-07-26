# Rerank 精排原理

## 核心思想

Rerank 用**交叉编码器（Cross-Encoder）**对初步检索结果做精细化排序，弥补初步检索"各自独立编码"的精度不足。

## 双塔 vs 交叉编码器

### 双塔模型（Bi-Encoder）— 初步检索用的方式

```
查询 → Encoder → 向量 A ─┐
                          ├─ cos(A, B)
文档 → Encoder → 向量 B ─┘
```

- 查询和文档**独立编码**，最后算相似度
- 文档向量可以**预计算**存储，检索时只编码查询，速度快
- 缺点：编码时看不到对方，无法捕捉深层交互

### 交叉编码器（Cross-Encoder）— Rerank 用的方式

```
[CLS] 查询 [SEP] 文档 [SEP] → Transformer → 相关性分数
```

- 查询和文档**拼接成一个序列**，做完整注意力计算
- 每个 token 都能看到查询和文档的所有 token，精度高
- 缺点：无法预计算，每对 (查询, 文档) 都要跑一遍模型，速度慢

## 为什么不全用 Cross-Encoder？

| 场景 | 文档量 | 耗时 |
|---|---|---|
| 全量 Cross-Encoder | 100 万篇 | 几十分钟 |
| 粗筛 + Cross-Encoder | 先筛到 50 篇，再精排 | 几秒 |

所以工程上分两步：
1. **粗筛**：BM25 + 向量检索，毫秒级从大量文档中召回少量候选
2. **精排**：Rerank 对候选文档逐对打分，秒级返回最终 Top-K

## 类比

- **初步检索** = 看简历关键词和岗位描述的匹配度，快速筛出 20 人
- **Rerank** = 把简历和岗位描述放在一起仔细对比，精排 Top 5

## 在我们的代码中

```python
# 1. 粗筛：BM25 + 向量 + RRF，召回 k*3 个候选
candidates = fused[: k * 3]

# 2. 精排：Rerank 逐对打分，返回 top-k
rerank_results = self.reranker.rerank(query, candidate_texts, top_n=k)
```

`ZhipuReranker.rerank()` 内部调用智谱 API，模型对每个 (query, document) 对做交叉编码，返回 `relevance_score`，按分数排序。
