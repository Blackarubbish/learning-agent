# 16 - Agent Memory 实践

## 目标

实现一个带双层记忆的 **MemoryAgent**：

1. **ShortTermMemory**：滑动窗口缓冲，记住当前会话最近 N 轮对话
2. **LongTermMemory**：FAISS 向量存储，跨会话持久化用户关键信息
3. **MemoryAgent**：整合短期+长期记忆，生成个性化响应

## 前置知识

- 第 12 章 Agent 核心概念（ReAct 循环）
- 第 15 章 Function Calling（LLM 调用模式）
- 第 04 章 RAG Part 2（FAISS 向量存储）

## 运行方式

```bash
# 填写 starter.py 的 TODO 后运行
cd learning/stage3-agent-development/16-agent-memory/practice
python starter.py

# 查看参考实现
python solution.py
```
