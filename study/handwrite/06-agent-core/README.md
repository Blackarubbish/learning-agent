# 06 — 通用 Agent 框架

## 目标

融合 02-05 的范式，设计一个可扩展的通用 Agent 基类。

## 核心概念

类似 opencode agent 的核心循环：

```
while not done:
    response = llm.invoke(messages + tools)
    if response has tool_calls:
        for tool_call in tool_calls:
            result = execute_tool(tool_call)
            messages.append(ToolMessage(result))
    else:
        done = True
        return response.content
```

## 你需要实现

1. **Agent 基类**：定义 `run()` 接口，支持 Function Calling 格式的工具调用
2. **工具注册**：装饰器或字典注册工具，自动生成 JSON Schema
3. **策略模式**：通过 strategy 参数切换 ReAct / Plan-and-Solve / ReWOO / Reflection 模式
4. **状态观测**：暴露中间状态（回调或 yield），支持 stream 模式

## 运行

```bash
uv run handwrite/06-agent-core/starter.py
```
