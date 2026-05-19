# 18 - 研究助手 Agent 综合实战

## 目标

整合阶段 3（ch12-17）全部核心能力，构建一个能搜索知识、摘要文本、持久化记忆的研究助手 Agent。

## 整合的技能

| 章节 | 能力 | 在项目中的位置 |
|------|------|---------------|
| 12/15 | FC Agent 循环 | `ResearchAssistant.run()` — bind_tools + ToolMessage |
| 13 | 工具工程 | `search_knowledge` 信息抽象，`summarize_text` 结构化输出 |
| 16 | 双层记忆 | `ShortTermMemory` 会话缓冲 + `LongTermMemory` FAISS 持久化 |
| 17 | 错误反射 | `classify_error` 三分类 + 结构化反馈 + 降级策略 |

## 架构

```
用户输入
  → [长期记忆检索] 从 FAISS 检索相关偏好
  → [短期记忆注入] 加载最近对话历史
  → [FC Agent 循环]
      ├── search_knowledge → 向量检索知识库
      ├── summarize_text    → LLM 摘要
      ├── save_note         → 写入长期记忆
      └── 失败 → 错误分类 → 反馈 → 重试/降级
  → [更新短期记忆]
  → 最终答案
```

## 4 个 TODO

| TODO | 内容 | 涉及章节 |
|------|------|---------|
| 1a-1c | 实现三个工具函数（search_knowledge / summarize_text / save_note） | ch13 |
| 1d | 定义 FC JSON Schema | ch15 |
| 2 | 实现 FC Agent 循环（bind_tools + ToolMessage） | ch15 |
| 3 | 集成错误反射（分类→反馈→重试/降级） | ch17 |
| 4 | 编写 5 个测试场景 | ch12-17 综合 |

## 前置知识

- 完成 12-17 章全部内容

## 运行方式

```bash
make run f=learning/stage3-agent-development/18-weekly-summary/practice/starter.py
```
