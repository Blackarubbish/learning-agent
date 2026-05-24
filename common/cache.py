"""LLM 缓存模块 — 精确匹配缓存 + 语义相似度缓存

两种缓存策略互补：
- ExactMatchCache: 完全相同的问题直接返回缓存，适合高频重复查询
- SemanticCache: 语义相似的查询共享缓存，适合同义改写场景

Usage:
    from common.cache import ExactMatchCache, SemanticCache
    from fakeredis import FakeRedis

    r = FakeRedis()
    exact = ExactMatchCache(r, ttl=3600)
    semantic = SemanticCache(r, embeddings, ttl=3600, threshold=0.92)
"""

import hashlib
import json
from typing import Optional

from fakeredis import FakeRedis


class ExactMatchCache:
    """精确匹配缓存 — SHA256(prompt) 作为缓存 key。

    只有字符级完全相同的 prompt 才会命中。
    适用场景：高频完全相同的查询（如系统 FAQ、固定 prompt 模板）。
    """

    def __init__(self, redis: FakeRedis, ttl: int = 3600, prefix: str = "exact:"):
        self.redis = redis
        self.ttl = ttl
        self.prefix = prefix

    def _make_key(self, prompt: str) -> str:
        """SHA256 哈希，保证任意长度 prompt 都能生成定长 key。"""
        return self.prefix + hashlib.sha256(prompt.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        result = self.redis.get(self._make_key(prompt))
        return result.decode() if result else None

    def set(self, prompt: str, response: str) -> None:
        self.redis.set(self._make_key(prompt), response, ex=self.ttl)

    def invalidate(self, prompt: str) -> None:
        self.redis.delete(self._make_key(prompt))


class SemanticCache:
    """语义缓存 — 用 embedding 相似度匹配"意思相近"的缓存结果。

    不是找字符相同的 prompt，而是找 embedding 向量最接近的历史缓存。
    适用场景：同义改写（"咋办" vs "怎么办"），多语言变体。
    """

    def __init__(
        self,
        redis: FakeRedis,
        embeddings,
        ttl: int = 3600,
        threshold: float = 0.92,
        prefix: str = "semantic:",
    ):
        self.redis = redis
        self.embeddings = embeddings
        self.ttl = ttl
        self.threshold = threshold
        self.prefix = prefix

    def _embed(self, text: str) -> list[float]:
        return self.embeddings.embed_query(text)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def _make_key(self, prompt: str) -> str:
        return self.prefix + hashlib.sha256(prompt.encode()).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        """遍历所有语义缓存条目，找到相似度最高且超过阈值的那个。"""
        query_embedding = self._embed(prompt)
        best_score = 0.0
        best_response = None

        for key in self.redis.scan_iter(match=f"{self.prefix}*"):
            raw = self.redis.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            cached_embedding = entry.get("embedding", [])
            score = self._cosine_similarity(query_embedding, cached_embedding)
            if score > best_score:
                best_score = score
                best_response = entry.get("response")

        return best_response if best_score >= self.threshold else None

    def set(self, prompt: str, response: str) -> None:
        embedding = self._embed(prompt)
        entry = {"response": response, "embedding": embedding}
        self.redis.set(self._make_key(prompt), json.dumps(entry), ex=self.ttl)

    def invalidate(self, prompt: str) -> None:
        self.redis.delete(self._make_key(prompt))
