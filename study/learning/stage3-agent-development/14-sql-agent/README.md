# 14 - SQL & 数据库工具

> ✅ practice 材料已创建

## 目标

让 Agent 通过 SQL 工具与数据库交互，实现自然语言→SQL→结构化结果的完整链路。结合第 13 章的工具工程原则（信息抽象、错误恢复），应用到数据库场景。

## 核心概念

| 概念 | 说明 | 对应 TODO |
|------|------|-----------|
| **Schema 探索** | Agent 需要先了解数据库结构（有哪些表、每列什么类型），类比先查目录再翻书 | TODO 1: db_schema |
| **SQL 安全校验** | 只允许 SELECT，拦截 INSERT/UPDATE/DELETE/DROP，防止 LLM 生成破坏性 SQL | TODO 2.1 |
| **结果限流 + 信息抽象** | 自动 LIMIT + 超限引导，防止百万行数据冲垮 LLM 上下文 | TODO 2.2-2.3 |
| **错误恢复** | SQL 执行失败时提示用 db_schema 确认列名，让 LLM 能自主修正 | TODO 2.4 |

## 练习文件

| 文件 | 说明 |
|------|------|
| `practice/starter.py` | 骨架代码 + 2 个 TODO，构建电商数据库的 Agent 工具 |
| `practice/solution.py` | 完整参考实现，含 11 项自检断言 |

## 数据库结构

```
products  (id, name, category, price, stock)       10 款商品
customers (id, name, city, level)                   8 位客户
orders    (id, customer_id, product_id, quantity, date, status)  15 条订单
```

## 运行方式

```bash
make run f=learning/stage3-agent-development/14-sql-agent/practice/starter.py
make run f=learning/stage3-agent-development/14-sql-agent/practice/solution.py
```

## 参考来源

- [AgentGuide 学习路线](https://github.com/adongwanai/AgentGuide) — Day 17
