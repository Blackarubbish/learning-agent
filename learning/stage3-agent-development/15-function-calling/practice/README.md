# 15 - Function Calling 实战

## 目标

对比传统 ReAct（文本解析工具调用）和 Function Calling（JSON Schema 定义工具），理解 FC 在解析可靠性和并行调用上的优势。

## 核心概念

| 概念 | 说明 |
|------|------|
| **Function Calling** | LLM 原生支持的函数调用机制，用 JSON Schema 定义工具参数 |
| **bind_tools** | 将工具定义绑定到 LLM，由模型直接返回结构化 ToolCall |
| **ToolMessage** | FC 中工具返回结果的专用消息类型 |
| **tool_choice** | 控制工具调用行为的四种模式：auto / required / none / 指定工具 |

## FC vs ReAct

| 维度 | ReAct (文本解析) | Function Calling |
|------|-----------------|-----------------|
| 解析可靠性 | ~80%（正则解析易出错） | ~99%（模型原生输出） |
| 并行调用 | 不支持 | 原生支持 |
| 推理链可见性 | 高（Thought 显式输出） | 低（思考过程隐藏） |
| 适用场景 | 需要暴露推理过程、调试、教学 | 生产环境、需要可靠性 |

## 练习内容

| 文件 | 说明 |
|------|------|
| `starter.py` | 3 个 TODO：工具定义转 JSON Schema → bind_tools + ToolMessage 循环 → tool_choice 实验 |
| `solution.py` | 完整参考实现，13 项自检断言 |
| `challenge.py` | 举一反三：对比 FC 和 ReAct 在解析失败场景下的表现 |

## 前置知识

- 12 章 ReAct 循环
- 熟悉 JSON Schema 基础语法

## 运行方式

```bash
make run f=learning/stage3-agent-development/15-function-calling/practice/starter.py
```
