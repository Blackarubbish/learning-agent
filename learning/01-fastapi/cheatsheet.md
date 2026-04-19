# FastAPI 速查表

## 路由装饰器

| 方法 | 装饰器 | 用途 |
|------|--------|------|
| GET | `@app.get()` | 获取资源 |
| POST | `@app.post()` | 创建资源 |
| PUT | `@app.put()` | 更新资源 |
| DELETE | `@app.delete()` | 删除资源 |
| PATCH | `@app.patch()` | 部分更新 |

## 路由参数

```python
@app.get("/items/{item_id}")
async def get_item(item_id: int):  # 自动类型转换
    return {"item_id": item_id}
```

## 查询参数

```python
@app.get("/items/")
async def get_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

## 请求体

```python
class Item(BaseModel):
    name: str
    price: float
    tags: list[str] = []

@app.post("/items/")
async def create_item(item: Item):
    return item
```

## 可选参数

```python
def get_item(item_id: int, q: str | None = None):
    pass
```

## HTTPException

```python
from fastapi import HTTPException

if not found:
    raise HTTPException(status_code=404, detail="Not found")
```

## 响应模型

```python
@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    return item
```

## 运行

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 自动文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
