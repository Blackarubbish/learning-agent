# FastAPI 学习问题记录

## Q&A

---

### Q: Python语法怎么插入数据到一个dict？

**A:**

```python
# 方式1: 直接赋值
notes_db[item_id] = note

# 方式2: update
notes_db.update({item_id: note})

# 方式3: |= (Python 3.9+)
notes_db |= {item_id: note}
```

推荐方式1，最简洁。
