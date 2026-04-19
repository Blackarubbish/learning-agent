# LangChain 学习问题记录

## Q&A

---

### Q: LangChain 调用 OpenAI 不需要写入 openapi 的密钥吗？

**A:**

调用 OpenAI 需要配置 API key，有几种方式：

```python
# 方式1: 环境变量
import os
os.environ["OPENAI_API_KEY"] = "sk-..."

# 方式2: 代码中直接传入
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    api_key="sk-..."
)

# 方式3: .env 文件 + python-dotenv
# .env: OPENAI_API_KEY=sk-...
```

**生产环境推荐方式1或方式3，不要硬编码密钥。**
