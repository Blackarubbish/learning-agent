# FastAPI 核心理念（对比 Node.js）

## 1. 声明式路由 vs 过程式路由

**Node.js (Express)** - 过程式，先注册路由，再写处理逻辑：
```javascript
// Node.js
app.get('/items/:id', async (req, res) => {
  const itemId = req.params.id
  const q = req.query.q
  res.json({ itemId, q })
})
```

**FastAPI** - 声明式，路由和处理逻辑一体化：
```python
# FastAPI
@app.get("/items/{item_id}")
async def get_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

**核心区别**：
- Express: `app.METHOD(path, ...middlewares, handler)`
- FastAPI: `@app.METHOD(path)` 直接装饰 handler 函数

---

## 2. Pydantic Models = Node.js 的 Zod/类型验证

Node.js 中用 Zod 做请求体验证：
```javascript
// Node.js + Zod
const schema = z.object({
  name: z.string(),
  price: z.number(),
  tags: z.array(z.string()).optional()
})
```

FastAPI 用 Pydantic 做同样的事，且更简洁：
```python
# FastAPI + Pydantic
class Item(BaseModel):
    name: str
    price: float
    tags: list[str] = []

@app.post("/items/")
async def create_item(item: Item):  # 自动验证
    return item
```

**Pydantic 优势**：
- 类型声明即验证规则，无需重复定义
- 自动 JSON 反序列化
- 自动生成 TypeScript 类型（通过 FastAPI 的 openapi.json）

---

## 3. async/await 模式与 Node.js 完全一致

```python
# FastAPI - 与 Node.js 几乎一样
@app.get("/async")
async def async_handler():
    result = await some_async_operation()
    return result

@app.get("/sync")
def sync_handler():  # 不需要 async
    return "sync result"
```

**规则**：
- 有 `await` 必用 `async def`
- CPU 密集型用普通 `def`（FastAPI 会用线程池）
- Node.js 的 `setTimeout` 对应 Python 的 `asyncio.sleep`

---

## 4. 依赖注入 ≠ Node.js 中间件

Node.js 中间件：
```javascript
app.use(authMiddleware)  // 全局应用
app.get('/protected', authMiddleware, handler)  // 路径级
```

FastAPI 依赖注入更直观：
```python
# 定义依赖
def get_db():
    db = connect_to_db()
    yield db
    db.close()

# 使用依赖 - 像个普通参数
@app.get("/items")
async def read_items(db = Depends(get_db)):
    return db.query("SELECT * FROM items")
```

**与中间件的区别**：
- 中间件：拦截所有请求，可修改 req/res
- 依赖注入：按需获取"服务"，不拦截请求

---

## 5. 自动 OpenAPI 文档（Node.js 需手动配置）

Express 需要手动配置 swagger：
```javascript
// Node.js - 需要手动配置
const swaggerUi = require('swagger-ui-express')
const swaggerDocument = require('./swagger.json')
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerDocument))
```

FastAPI 自动生成：
```python
app = FastAPI()
# 启动后直接访问:
# http://localhost:8000/docs  (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

**访问 http://localhost:8000/docs 查看交互式 API 文档**

---

## 6. response_model = 自动序列化 + 过滤

```python
class UserIn(BaseModel):
    password: str  # 不应返回给客户端
    email: str

class UserOut(BaseModel):
    username: str
    email: str

@app.post("/users/", response_model=UserOut)
async def create_user(user: UserIn):
    # 返回时自动过滤掉 password
    return user
```

对比 Node.js 需要手动处理：
```javascript
// Node.js - 手动过滤
app.post('/users', (req, res) => {
  const { password, ...rest } = req.body
  res.json(rest)  // 手动过滤
})
```

---

## 核心问题自测

1. **FastAPI 的路由装饰器 `@app.get()` 和 Express 的 `app.get()` 本质区别是什么？**
   - 装饰器是声明式，路由和处理函数绑定同时发生；Express 是过程式，先有 app，再注册路由。

2. **Pydantic BaseModel 在 FastAPI 中的作用是什么？**
   - 自动验证请求体、自动序列化响应、自动生成 OpenAPI schema。

3. **FastAPI 的 `async def` 和普通 `def` 有什么区别？**
   - `async def` 用于 I/O 异步操作，`def` 用于同步/CPU密集操作（会自动用线程池）。

4. **FastAPI 的依赖注入和 Express 中间件有什么不同？**
   - 中间件拦截并处理请求流，依赖注入只是"按需获取服务"，不拦截请求。

5. **`response_model` 参数有什么用？**
   - 定义响应数据结构，自动过滤不必要的字段，自动处理序列化。

---

## 启动服务

```bash
uvicorn main:app --reload
```

访问 http://localhost:8000/docs 测试你的 API。
