# 第 29 章 — LangGraph 生产级 Agent 工作流

## 本章目标

理解 LangGraph 的核心抽象，并能手写一个极简 StateGraph：

- **State**：用字典/TypedDict 显式定义流程共享状态
- **Node**：每个节点是一个纯函数，接收 state 返回更新
- **Edge**：普通边固定连接两个节点
- **ConditionalEdge**：条件边根据状态动态决定下一个节点
- **START / END**：入口和出口标记
- **Checkpoint**：每步状态持久化，支持断点续跑

## 前置知识

- 第 12 章 ReAct 循环
- 第 15 章 Function Calling
- 第 26–28 章多 Agent 协调

## 本章练习

打开 `practice/starter.py`，按 TODO 提示补全 `StateGraph` / `CompiledGraph` / 工作流节点。

运行（项目使用 `make run` 自动设置 `PYTHONPATH`）：

```bash
make run f=learning/stage6-multi-agent/29-langgraph/practice/starter.py
```

完成后可对照 `practice/solution.py`。

## 关键问题

1. LangGraph 的 StateGraph 和 ReAct 里的 `while` 循环有什么本质区别？
2. ConditionalEdge 适合解决什么问题？
3. Checkpoint 在生产环境里为什么重要？
