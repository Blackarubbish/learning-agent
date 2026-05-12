# 13 - 自定义工具开发

> ✅ practice 材料已创建

## 目标

不只是"写个函数"，而是设计 **AI 友好的工具接口**。Agent 生产实践揭示：**70% 的工作是工具工程**，AI 只完成 30%。

## 核心概念（来自 AgentGuide 生产实践）

| 概念 | 说明 | 对应 TODO |
|------|------|-----------|
| **信息抽象** | 数据库查回 10000 行，Agent 只需要前 5 行 + 总数 | TODO 1: naive_search → smart_search |
| **状态反馈** | 操作部分成功时，如何告知 Agent 进度？ | TODO 2: batch_process |
| **错误恢复接口** | 工具失败时返回什么信息，让 Agent 知道如何修正？ | TODO 3: api_fetch |
| **扁平参数设计** | 嵌套 JSON 对 LLM 不友好，优先用扁平字符串参数 | api_fetch 的 param 设计 |

## 反面案例

如果工具只是 `return raw_response`，Agent 会因为上下文过载而无法决策——太多 token 冲垮推理能力。

## 练习文件

| 文件 | 说明 |
|------|------|
| `practice/starter.py` | 骨架代码 + 4 个 TODO，引导完成工具从"能用"到"好用"的升级 |
| `practice/solution.py` | 完整参考实现，含 14 项自检断言 |

## 运行方式

```bash
# 编写 starter.py 中的 TODO 后运行
make run f=learning/stage3-agent-development/13-custom-tools/practice/starter.py

# 查看完整参考实现
make run f=learning/stage3-agent-development/13-custom-tools/practice/solution.py
```

## 参考来源

- [AgentGuide 学习路线](https://github.com/adongwanai/AgentGuide) — Day 16
- `AgentGuide/resources/agent/ai-agent-production-challenges.md` — 第三部分"工具工程现实墙"
- [Anthropic Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
