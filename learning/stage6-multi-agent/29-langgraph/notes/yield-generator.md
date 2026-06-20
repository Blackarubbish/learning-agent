# Python yield 与生成器

## 一、它解决什么问题？

普通函数 `return` 只能一次性返回所有结果，调用者必须等全部计算完才能拿到数据。如果结果很多或计算很慢，会浪费内存且无法中途观察进度。

`yield` 让函数变成**生成器**：可以**算一个、交一个、暂停一下**，调用者按需取用。这样既省内存，又能实时看到中间状态。

## 二、核心原理（用类比解释）

普通函数像一台**自动售货机一次性吐出所有饮料**：你按下按钮，机器在里面全部灌装完，最后“砰”地一下把所有饮料堆在你面前。

生成器像一台**流水线上的机械臂**：

- 你按一下按钮，它做一瓶饮料，递给你
- 你不按，它就停在那里，记住做到哪一步
- 你再按，它从刚才停的位置继续做下一瓶
- 饮料厂不需要一次性把所有饮料都堆在仓库里

技术层面，`yield` 做两件事：

1. 把当前值交给调用者
2. **保存函数现场**，下次从 `yield` 之后继续执行，而不是从头开始

## 三、反面案例 —— 如果没有它，会发生什么？

假设 LangGraph 的 `stream` 用普通列表返回所有中间状态：

```python
def stream(self, state):
    results = []
    while 还有节点:
        # 跑节点、更新 state
        results.append(dict(state))
    return results
```

问题：

1. **内存浪费**：所有中间状态都要先存进 `results`，节点越多列表越大
2. **无法实时观测**：调用者必须等整个图跑完才能看到第一步的结果
3. **不够灵活**：如果调用者只想看前几个状态，函数也不得不跑完全部

用 `yield` 后，调用者每取一个状态，图就跑一步；不想看了随时停止，没跑完的节点不会执行。

## 四、我能用它做什么？（3 个具体场景）

1. **LangGraph 流式观测**：每跑完一个节点 `yield dict(state)`，前端可以实时展示 Agent 的思考步骤
2. **大文件逐行读取**：不用一次性读入内存，用生成器一次读一行处理
3. **无限序列 / 流式数据**：比如实时日志处理、传感器数据流，数据没有尽头，无法一次 `return` 完

## 五、和已有知识的关联（指向 CONCEPT_MAP.md）

- [[21-async]] `asyncio` 也追求“不阻塞、按需推进”，但 `yield` 是**同步**的生成器机制，`await` 是**异步**的协程机制；两者都是“暂停-恢复”思想的不同实现
- [[29-langgraph]] LangGraph 的 `stream()` 依赖 `yield` 把每个节点后的 state 暴露给调用者，是实现 HITL（人在回路）和调试的基础
- 普通 `return` 与 `yield` 的区别：前者是“全部做完交卷”，后者是“做一题问一题”

## 六、我还困惑的地方（留白后续补充）

- 生成器表达式 `(x for x in range(10))` 和列表推导 `[x for x in range(10)]` 的内存差异具体有多大？
- `yield from` 在嵌套生成器中的作用是什么？
- 生成器函数里 `return value` 到底去了哪里？什么时候需要捕获 `StopIteration`？

## 关键语法速查

```python
# 普通函数：一次返回全部
def normal():
    return [1, 2, 3]

# 生成器函数：逐个产出
def gen():
    yield 1
    yield 2
    yield 3

# 使用方式 1：for 循环or value in gen():
    print(value)

# 使用方式 2：转成列表（会消耗整个生成器）
values = list(gen())

# 在 LangGraph stream 中的典型模式
def stream(self, state):
    current = self.entry_point
    while current != END:
        # 跑节点、合并 updates
        updates = self.nodes[current](state)
        if updates:
            state.update(updates)
        yield dict(state)  # 每完成一个节点，交出一个状态副本
        current = self.next_node(current, state)
```

## 一句话总结

> `return` 是“全部算完交卷”，`yield` 是“算一步交一步，还能下次接着算”。
