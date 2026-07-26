# 第 30 章 — 实战项目：智能客服工单处理系统

> **考核模式**：本章没有 starter.py / solution.py。你拿到的是**产品文档 + 代码框架 + 功能测试**。你的任务是独立实现产品功能，跑通所有测试。

---

## 一、项目背景

你所在的团队接到一个需求：为某 SaaS 平台构建**智能客服工单处理系统**。

当前客服团队每天处理 200+ 条用户工单，其中 60% 是重复性问题（"怎么退款""登录不了""这个功能怎么用"）。产品经理想用 AI Agent 自动处理这 60% 的工单，人类客服只处理复杂 case。

你的任务是：用**两种 Multi-Agent 框架**各实现一版，做技术选型对比。

---

## 二、功能需求

### FR-1: 工单分类

**场景**：用户提交问题文本，系统自动判断问题类型。

**输入**：用户原始问题（字符串）
**输出**：问题类型（`"technical"` / `"billing"` / `"general"`），以及分类理由

**验收标准**：
- "无法登录" → `technical`
- "怎么退款" → `billing`
- "你们支持哪些语言" → `general`
- LLM 分类，不是关键词匹配

---

### FR-2: 知识库检索

**场景**：根据分类结果，在对应的知识库分区中检索相关信息。

**输入**：问题类型 + 用户原始问题
**输出**：1-2 条相关知识库条目（标题 + 内容）

**知识库数据**（已在代码框架中提供）：

| 类型 | 条目 |
|------|------|
| technical | 登录问题排查 / API 报错 401 / 数据同步延迟 |
| billing | 退款流程 / 发票申请 / 套餐变更 |
| general | 支持语言 / 数据隐私 / SLA 承诺 |

**验收标准**：
- 检索结果与问题类型匹配
- 检索结果与用户问题语义相关
- 如果没有匹配结果，返回空列表而非编造

---

### FR-3: 回复生成

**场景**：基于知识库检索结果，生成专业、有帮助的客服回复。

**输入**：用户原始问题 + 分类结果 + 检索到的知识条目
**输出**：一段客服回复文本（50-200 字），包含：
- 对用户问题的确认
- 具体的解决步骤或信息
- 如果知识库信息不足，诚实告知并提供替代方案

**验收标准**：
- 回复语气专业、友好
- 回复内容基于知识库事实，不编造
- 回复长度适中（50-200 字）

---

### FR-4: 质量审核

**场景**：审核生成的回复是否符合质量标准，不符合则退回重新生成。

**输入**：生成的回复 + 用户原始问题
**输出**：审核结论（`"approved"` / `"rejected"`）+ 审核意见

**审核标准**：
- 回复是否解决了用户问题？
- 回复是否基于知识库（而非编造）？
- 语气是否专业友好？
- 长度是否适中？

**验收标准**：
- 符合标准的回复 → `approved`
- 明显偏离问题 / 编造内容 / 语气不当 → `rejected`，审核意见指出具体问题

---

### FR-5: 完整工单处理流水线

**场景**：将 FR-1 到 FR-4 串联成完整流水线，处理一条用户工单。

**输入**：用户原始问题（字符串）
**输出**：
- 最终回复（如果审核通过）
- 或者退回后重新生成的回复（最多退回 1 次，第二次必须输出）

**验收标准**（end-to-end）：
- 输入 "无法登录" → 走 technical 路径 → 最终回复包含登录排查相关内容
- 输入 "怎么退款" → 走 billing 路径 → 最终回复包含退款流程相关内容
- 输入 "你是谁" → 无匹配知识库 → 诚实告知无法处理

---

## 三、Agent 角色定义

### CrewAI 风格（5 个角色）

| 角色 | 职责 | 关键 Prompt 要素 |
|------|------|-----------------|
| **分类专员** (Classifier) | 判断问题类型 | 只能输出 technical/billing/general |
| **技术专家** (TechSupport) | 处理技术问题 | 熟悉登录、API、数据同步 |
| **账单专员** (BillingSupport) | 处理账单问题 | 熟悉退款、发票、套餐 |
| **通用客服** (GeneralSupport) | 处理一般咨询 | 熟悉公司政策、产品信息 |
| **审核员** (Reviewer) | 审核回复质量 | 按 4 条标准审核，给出 approved/rejected |

### LangGraph 风格（节点映射）

| 节点 | 对应角色 | 功能 |
|------|---------|------|
| `classify` | 分类专员 | FR-1 |
| `research` | - | FR-2（纯数据检索，不调 LLM） |
| `draft` | 技术/账单/通用（按分类路由） | FR-3 |
| `review` | 审核员 | FR-4 |
| `route_by_category` | - | 条件边：根据分类结果路由到不同 draft 策略 |

---

## 四、工作流对比

```
CrewAI 风格（顺序流水线）:
  classify → [research / draft 按类型] → review → 通过? → 输出
                                                ↓ 不通过
                                              draft → review → 输出

LangGraph 风格（状态机）:
  START → classify → route_by_category ─┬→ draft_tech → review
                                        ├→ draft_billing → review
                                        └→ draft_general → review
                                              ↑ 不通过      ↓ 通过
                                              └──────────→ END
```

关键差异：
- **CrewAI**: Task 之间有 context 依赖链，审核不通过通过条件逻辑处理
- **LangGraph**: 条件边 `route_by_category` 实现路由，`review` 的条件边决定结束或回退

---

## 五、技术约束

1. **依赖**: 使用真实 `crewai` + `langgraph` 框架（已安装），外加项目 `common` 模块
2. **CrewAI LLM**: 需要在 `get_crewai_llm()` 中配置 DeepSeek（CrewAI 通过 litellm 调用，支持 `deepseek/deepseek-chat` 或 `openai/` 前缀 + base_url）
3. **LangGraph LLM**: 节点函数内使用 `get_or_create_llm(temperature=0)` 调用 DeepSeek
4. **知识库**: 使用 `KNOWLEDGE_BASE` 字典，不需要真实向量数据库
5. **框架基类**: 无需自己实现 — `main.py` 已导入真实的 `crewai.Agent/Task/Crew/Process` 和 `langgraph.graph.StateGraph/START/END`

---

## 六、交付物

1. `main.py` — 完整实现，所有 TODO 已填充
2. 运行 `.venv/bin/python tests/test_crewai.py` — 全部通过
3. 运行 `.venv/bin/python tests/test_langgraph.py` — 全部通过
4. 运行 `.venv/bin/python tests/test_comparison.py` — 全部通过
5. `notes/qa.md` — 费曼笔记（用自己的话回答核心问题）

---

## 七、参考资料

- [Agent 框架对比](../../AgentGuide/resources/agent/frameworks.md) — 框架选型决策矩阵
- [第 26 章 Swarm](../26-swarm/) — Handoff 机制回顾
- [第 27 章 AutoGen](../27-autogen/) — GroupChat 回顾
- [第 28 章 CrewAI](../28-crewai/) — Agent/Task/Crew 回顾
- [第 29 章 LangGraph](../29-langgraph/) — StateGraph 回顾
