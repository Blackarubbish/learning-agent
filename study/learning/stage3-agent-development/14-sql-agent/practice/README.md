# 14 - SQL & 数据库工具

## 目标

让 Agent 通过 SQL 工具与数据库交互，实现自然语言 → SQL → 结构化结果的完整链路。结合第 13 章的工具工程原则应用到数据库场景。

## 核心概念

| 概念 | 说明 |
|------|------|
| **Schema 探索** | Agent 先了解数据库结构（表名、列名、类型），类比"先查目录再翻书" |
| **SQL 安全校验** | 只允许 SELECT，拦截 INSERT/UPDATE/DELETE/DROP，防止 LLM 幻觉导致数据灾难 |
| **结果限流 + 信息抽象** | 自动 LIMIT + 超限引导，防止百万行数据冲垮 LLM 上下文 |
| **错误恢复** | SQL 执行失败时提示用 db_schema 确认列名，让 LLM 自主修正 |

## 数据库结构

```
products  (id, name, category, price, stock)      10 款商品
customers (id, name, city, level)                  8 位客户
orders    (id, customer_id, product_id, quantity, date, status)  15 条订单
```

## 两个工具

| 工具 | 功能 | 核心训练点 |
|------|------|-----------|
| `db_schema` | 返回表结构和示例数据 | Schema 探索 + 信息抽象 |
| `db_query` | 执行只读 SQL 查询 | 安全校验 + 结果限流 + 错误恢复 |

## 前置知识

- 12 章 ReAct 循环
- 13 章工具工程（信息抽象、错误恢复接口）

## 运行方式

```bash
make run f=learning/stage3-agent-development/14-sql-agent/practice/starter.py
```
