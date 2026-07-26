"""
第 29 章 — LangGraph 生产级 Agent 工作流（手动版）

参考实现。重点不是复刻 LangGraph，而是把「状态 + 节点 + 边 + 条件路由」
这些核心抽象用最小代码表达出来。
"""

from collections.abc import Callable
from typing import Any

from common import check, reset, section, summary

START = "__start__"
END = "__end__"


class StateGraph:
    """LangGraph 风格的状态图：用 Node + Edge 描述 Agent 工作流。"""

    def __init__(self, state_schema: type[dict]) -> None:
        # state_schema 仅做类型契约示意，运行时不强校验
        self.state_schema = state_schema
        self.nodes: dict[str, Callable[[dict], dict[str, Any]]] = {}
        self.edges: dict[str, str] = {}
        self.conditional_edges: dict[str, tuple[Callable[[dict], str], dict[str, str]]] = {}
        self.entry_point: str | None = None

    def add_node(self, name: str, fn: Callable[[dict], dict[str, Any]]) -> "StateGraph":
        """添加一个节点，fn 接收当前 state，返回要合并的更新。"""
        self.nodes[name] = fn
        return self

    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        """添加普通边：从 from_node 固定走到 to_node。"""
        self.edges[from_node] = to_node
        return self

    def add_conditional_edges(
        self,
        from_node: str,
        condition: Callable[[dict], str],
        path_map: dict[str, str],
    ) -> "StateGraph":
        """
        添加条件边：从 from_node 出发，根据 condition(state) 的返回值
        在 path_map 中查找下一个节点名。
        """
        self.conditional_edges[from_node] = (condition, path_map)
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        """设置图的入口节点。"""
        self.entry_point = name
        return self

    def compile(self) -> "CompiledGraph":
        """编译图为可运行对象。"""
        return CompiledGraph(self)


class CompiledGraph:
    """编译后的图，支持 invoke（一次性运行）和 stream（流式观测）。"""

    def __init__(self, graph: StateGraph) -> None:
        self.graph = graph
        self.checkpoints: list[dict] = []

    def _merge_updates(self, state: dict, updates: dict[str, Any]) -> dict:
        """把节点返回的 updates 合并到 state 中，返回新的 state。"""
        state.update(updates)
        return state

    def _next_node(self, current: str, state: dict) -> str:
        """根据普通边或条件边决定下一个节点。"""
        # 优先检查条件边：条件函数返回 path_map 中的 key
        if current in self.graph.conditional_edges:
            condition, path_map = self.graph.conditional_edges[current]
            decision = condition(state)
            return path_map.get(decision, END)

        # 否则走普通边
        return self.graph.edges.get(current, END)

    def invoke(self, state: dict) -> dict:
        """从入口节点开始运行，直到走到 END。"""
        if self.graph.entry_point is None:
            raise ValueError("必须先调用 set_entry_point 设置入口节点")

        current = self.graph.entry_point

        while current != END:
            # 运行前保存 checkpoint（深拷贝避免后续更新污染历史）
            self.checkpoints.append(dict(state))

            node_fn = self.graph.nodes.get(current)
            if node_fn is None:
                raise ValueError(f"节点 {current} 未定义")

            updates = node_fn(state)
            state = self._merge_updates(state, updates)
            current = self._next_node(current, state)

        # 保存最终状态
        self.checkpoints.append(dict(state))
        return state

    def stream(self, state: dict):
        """流式运行图，每完成一个节点就 yield 当前 state 副本。"""
        if self.graph.entry_point is None:
            raise ValueError("必须先调用 set_entry_point 设置入口节点")

        current = self.graph.entry_point
        yield dict(state)

        while current != END:
            node_fn = self.graph.nodes[current]
            updates = node_fn(state)
            state = self._merge_updates(state, updates)
            current = self._next_node(current, state)
            yield dict(state)


def research_node(state: dict) -> dict:
    """研究节点：补充一个事实到 facts 列表。"""
    facts = list(state.get("facts", []))
    topic = state.get("topic", "LangGraph")
    new_fact = f"事实 {len(facts) + 1}：{topic} 支持声明式状态机"
    return {"facts": facts + [new_fact], "steps": state.get("steps", 0) + 1}


def analyze_node(state: dict) -> dict:
    """分析节点：判断是否已经收集到足够事实。"""
    enough = len(state.get("facts", [])) >= 2
    return {"ready": enough}


def decide_after_analyze(state: dict) -> str:
    """条件边函数：根据 ready 决定下一步。"""
    return "write" if state.get("ready") else "research"


def write_node(state: dict) -> dict:
    """写作节点：基于 facts 生成最终答案。"""
    facts = state.get("facts", [])
    answer = "; ".join(facts) + "。"
    return {"answer": answer}


if __name__ == "__main__":
    reset()

    section("1. 构建 StateGraph")

    graph = StateGraph(dict)
    graph.add_node("research", research_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("write", write_node)

    graph.set_entry_point("research")
    graph.add_edge("research", "analyze")
    graph.add_conditional_edges(
        "analyze",
        decide_after_analyze,
        {"research": "research", "write": "write"},
    )
    graph.add_edge("write", END)

    app = graph.compile()

    section("2. 运行图")

    initial_state = {"topic": "LangGraph", "facts": [], "steps": 0}
    final_state = app.invoke(initial_state)

    print(f"最终 state: {final_state}")

    check("收集了至少 2 个事实", len(final_state.get("facts", [])) >= 2)
    check("生成了最终答案", bool(final_state.get("answer")))
    check("答案包含事实内容", "事实 1" in final_state.get("answer", ""))

    section("3. 检查 Checkpoint")

    check("Checkpoint 记录了中间状态", len(app.checkpoints) >= 3)
    check("Checkpoint 包含最终状态", app.checkpoints[-1].get("answer") == final_state.get("answer"))

    section("4. 流式运行")

    stream_states = list(app.stream(initial_state))
    check("stream 至少产出 3 个状态快照", len(stream_states) >= 3)
    check("stream 最终状态包含答案", bool(stream_states[-1].get("answer")))

    summary()
