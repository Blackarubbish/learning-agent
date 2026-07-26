# 第 28 章 — CrewAI 角色驱动的任务协作

## 本章目标

理解 CrewAI 的核心设计哲学：**用「角色（Role）」而非「提示词技巧」来组织多 Agent 协作**。

你将手动实现一个极简 CrewAI，掌握其三段式定义：

```
Agent(role + goal + backstory)
    ↓
Task(description + expected_output + agent + context)
    ↓
Crew(agents + tasks + process)
```

## 核心问题

当任务可以被拆成一条流水线时，**谁来保证每个步骤都有合适的角色执行、按正确的顺序执行、并把中间结果传递给下一步？**

CrewAI 的答案是：
- **Agent**：定义「谁来做」，用 role/goal/backstory 塑造行为
- **Task**：定义「做什么」，用 description/expected_output 明确交付物
- **Crew**：定义「怎么做」，用 Process 控制执行模式

## 两种 Process

| Process | 含义 | 适用场景 |
|---------|------|---------|
| `sequential` | 按 tasks 列表顺序依次执行 | 流程固定、步骤依赖明确的流水线 |
| `hierarchical` | 引入 manager Agent 动态分配任务 | 任务有优先级、需要协调员的复杂项目 |

## 本章任务

完成 `practice/starter.py` 中的 TODO：

1. 实现 `Agent` 的基本结构
2. 实现 `Task` 的 context 依赖传递
3. 实现 `Crew` 的 `sequential` 执行流程
4. 实现 `Crew` 的 `hierarchical` 执行流程

## 运行方式

项目使用 `make run` 自动设置 `PYTHONPATH`：

```bash
make run f=learning/stage6-multi-agent/28-crewai/practice/starter.py
```

## 前置知识

- 第 12 章 ReAct 循环
- 第 15 章 Function Calling
- 第 26 章 Swarm Handoff
- 第 27 章 AutoGen GroupChat
