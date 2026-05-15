# 15 - Function Calling 实战

> ✅ practice 材料已创建

## 目标

理解 Function Calling 的本质——从 ReAct 的"文本解析"升级到 LLM 原生的"结构化工具调用"。模型被训练输出 `tool_calls` token，不再需要正则解析 Thought/Action/Action Input。

## 核心概念

| 概念 | ReAct（第 12 章） | Function Calling（本章） |
|------|-------------------|-------------------------| 
| **工具调用方式** | 文本输出 → 正则解析 | 结构化 tool_calls token |
| **解析可靠性** | 受格式偏差/嵌套 JSON 影响 | 100% 解析成功率 |
| **是否调工具** | Prompt 强制输出 Action | 模型自主决定 |
| **并行调用** | 不支持（一次一个） | 支持（一次多个 tool_calls） |
| **代码复杂度** | ~100 行 ReAct 循环 + 解析器 | ~30 行 FC 循环 |





## 练习文件

| 文件 | 说明 |
|------|------|
| `practice/starter.py` | 骨架代码 + 3 个 TODO |
| `practice/solution.py` | 完整参考实现，含 FC vs ReAct 对比实验 + tool_choice 实验 |
| `practice/challenge.py` | 综合挑战（可选）：构建搜索+计算+摘要的 FC Agent |

## TODO 拆解

| TODO | 主题 | 要实现的 |
|------|------|---------|
| **TODO 1** | 工具定义 | 将 3 个工具转换为 OpenAI Function Calling JSON Schema 格式 |
| **TODO 2** | FC 循环 | 用 `bind_tools` + `AIMessage.tool_calls` + `ToolMessage` 实现循环 |
| **TODO 3** | tool_choice 控制 | 实验 `auto` / `required` / `none` / 指定工具四种模式的行为差异 |

## 学习资料总结

> 从 [AgentGuide](https://github.com/adongwanai/AgentGuide) 路线和相关资源中提取。学习前先通读，建立全局认知。

### 本章在 Agent 开发知识体系中的位置

```
Agent 核心概念 → 自定义工具 → SQL 工具 → Function Calling(本章) → Agent Memory → 错误处理
```

### 核心阅读（必读）

| 资源 | 内容 | 来源 |
|------|------|------|
| [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling) | 官方文档：tool_choice / parallel tools / structured output | AgentGuide Day 18 |
| [GPT Best Practices](https://platform.openai.com/docs/guides/gpt-best-practices) | 工具描述编写策略、提示词配合技巧 | AgentGuide Day 18 |
| [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Agent 设计第一性原理：何时用 workflow，何时用 agent | Anthropic 官方 |

### 进阶阅读（加深理解）

| 资源 | 内容 | 来源 |
|------|------|------|
| [AI Agent 生产环境实践](AgentGuide/resources/agent/ai-agent-production-challenges.md) | 70%工作在工具端而非 AI，工具工程决定 Agent 上限 | AgentGuide 资源库 |
| [上下文工程最佳实践](AgentGuide/docs/02-tech-stack/11-context-engineering-practices.md) | Offload/Retrieve/Compress/Isolate — 如何管理工具返回的大量信息 | AgentGuide 技术栈文档 |
| [Toolformer 论文](https://arxiv.org/abs/2302.04761) | LLM 自学使用工具的开创性工作，理解工具调用的训练本质 | AgentGuide 必读论文 |

### 本章要掌握的核心概念

| 概念 | 一句话说明 | 对应 TODO |
|------|-----------|-----------|
| **JSON Schema 工具定义** | 用结构化 Schema 替代 ReAct 的文本工具描述，模型输出 tool_calls token 而非自由文本 | TODO 1 |
| **bind_tools + ToolMessage 循环** | `bind_tools` 绑定工具 → `invoke` 获取响应 → `tool_calls` 判断 → `ToolMessage` 反馈结果 → 循环 | TODO 2 |
| **tool_choice 控制** | `auto`(默认)/`required`(强制)/`none`(禁止)/指定工具 — 精细控制模型的调用行为 | TODO 3 |

### FC vs ReAct 对比（本质差异）

| 维度 | ReAct（第 12 章） | Function Calling（本章） |
|------|-------------------|-------------------------|
| 工具定义方式 | Prompt 文本描述 | JSON Schema 结构化定义 |
| 调用输出 | 自由文本（需正则解析） | 结构化 tool_calls token |
| 解析可靠性 | ~90%（受格式/嵌套影响） | 100% |
| 并行调用 | 不支持 | 原生支持 |
| 模型自主决策 | Prompt 强制输出 Action | 模型自主决定是否调用 |
| 代码量 | ~100行（循环+解析器） | ~30行 |

### 工具工程核心原则（来自生产实践）

1. **信息抽象** — 工具返回大量数据时，只给摘要+引导，让 LLM 按需深入，防止上下文爆炸
2. **错误保留** — 工具调用失败的结果要保留在上下文中，模型能从失败中学习
3. **描述即接口** — 工具描述是 LLM 理解工具的唯一途径，描述质量决定调用准确率
4. **简单优先** — 能用一个工具解决的问题不要拆成两个，减少 LLM 的决策负担

## 关键 API

```python
llm_with_tools = llm.bind_tools(TOOLS_FC)        # 绑定工具
response = llm_with_tools.invoke(messages)         # 返回 AIMessage
response.tool_calls                                # [{"name": ..., "args": {...}, "id": "..."}]
ToolMessage(content=result, tool_call_id=tc["id"]) # 工具结果反馈
```

## 运行方式

```bash
make run f=learning/stage3-agent-development/15-function-calling/practice/starter.py
make run f=learning/stage3-agent-development/15-function-calling/practice/solution.py
```

## 参考来源

- [AgentGuide 学习路线](https://github.com/adongwanai/AgentGuide) — Day 18
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
