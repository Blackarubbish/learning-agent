# FastAPI 练习（可选）

以下练习用于巩固 FastAPI 核心概念，可选择性完成。

## 快速验证

启动服务后访问 http://localhost:8000/docs 查看自动生成的交互式文档。

```bash
uvicorn main:app --reload --port 8000
```

## 验证 Pydantic 验证

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    price: float


@app.post("/items/")
async def create_item(item: Item):
    return item
```

**测试**：POST 一个 `{"name": "test", "price": "not_a_number"}` 看 Pydantic 如何自动返回 422 验证错误。
