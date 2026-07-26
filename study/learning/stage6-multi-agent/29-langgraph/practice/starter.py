"""
第 29 章 — LangGraph 生产级 Agent 工作流（手动版）

目标：实现一个极简 StateGraph，理解：
- State：流程中所有节点共享的字典状态
- Node：接收 state 返回 state 更新的函数
- Edge：普通边，固定连接两个节点
- ConditionalEdge：条件边，根据 state 动态路由
- START / END：入口和出口标记
- Checkpoint：每步保存状态，支持断点续跑
"""

from collections.abc import Callable
from typing import Any

from common import check, reset, section, summary

START = "__start__"
END = "__end__"


class StateGraph:
    """LangGraph 风格的状态图：用 Node + Edge 描述 Agent 工作流。"""

    def __init__(self, state_schema: type[dict]) -> None:
        self.state_schema = state_schema
        self.nodes: dict[str, Callable[[dict], dict[str, Any]]] = {}
        self.edges: dict[str, str] = {}
        self.conditional_edges: dict[str, tuple[Callable[[dict], str], dict[str, str]]] = {}
        self.entry_point: str | None = None

    def add_node(self, name: str, fn: Callable[[dict], dict[str, Any]]) -> "StateGraph":
        """添加一个节点，fn 接收当前 state，返回要合并的更新。"""
        # TODO 1: 把 name 和 fn 注册到 self.nodes
        self.nodes[name] = fn
        return self

    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        """添加普通边：从 from_node 固定走到 to_node。"""
        # TODO 2: 把边注册到 self.edges
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
        # TODO 3: 把条件边注册到 self.conditional_edges
        self.conditional_edges[from_node] = (condition, path_map)
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        """设置图的入口节点。"""
        # TODO 4: 设置 self.entry_point
        self.entry_point = name
        return self

    def compile(self) -> "CompiledGraph":
        """编译图为可运行对象。"""
        # TODO 5: 返回 CompiledGraph(self)
        return CompiledGraph(self)


class CompiledGraph:
    """编译后的图，支持 invoke（一次性运行）和 stream（流式观测）。"""

    def __init__(self, graph: StateGraph) -> None:
        self.graph = graph
        self.checkpoints: list[dict] = []

    def invoke(self, state: dict) -> dict:
        """
        从入口节点开始运行，直到走到 END。

        规则：
        1. 当前节点运行前，先把当前 state 保存到 checkpoints
        2. 调用节点函数，得到 updates，合并到 state（同名 key 覆盖，新 key 添加）
        3. 根据普通边或条件边决定下一个节点
        4. 如果下一个节点是 END，保存最终 state 到 checkpoints 并返回
        """
        # TODO 6: 实现 invoke 主循环
        # 提示：从 self.graph.entry_point 开始，循环执行节点，
        # 调用节点函数合并 updates，决定下一步，直到走到 END
        current_node = self.graph.entry_point
        print(f"[invoke] 入口节点: {current_node}")
        while current_node != END:
            self.checkpoints.append(dict(state))
            print(f"\n[invoke] >>> 进入节点: {current_node}")
            print(f"[invoke] 当前 state: {state}")

            node_func = self.graph.nodes[current_node]
            if node_func:
                updates = node_func(state)
                print(f"[invoke] 节点返回 updates: {updates}")
                if updates:
                    state.update(updates)
                    print(f"[invoke] 合并后 state: {state}")

            if current_node in self.graph.conditional_edges:
                condition, path_map = self.graph.conditional_edges[current_node]
                decision = condition(state)
                next_node = path_map.get(decision, END)
                print(f"[invoke] 条件边决策: {decision} -> 下一节点: {next_node}")
            elif current_node in self.graph.edges:
                next_node = self.graph.edges.get(current_node, END)
                print(f"[invoke] 普通边: {current_node} -> {next_node}")
            else:
                next_node = END
                print("[invoke] 无出边，默认 -> END")

            current_node = next_node
        self.checkpoints.append(dict(state))
        print(f"\n[invoke] 到达 END，最终 state: {state}")
        return state

    def stream(self, state: dict):
        """
        流式运行图，每完成一个节点就 yield 当前 state 副本。
        """
        # TODO 7: 在 invoke 基础上 yield 每一步的 state 快照
        current_node = self.graph.entry_point
        print(f"\n[stream] 入口节点: {current_node}")
        while current_node != END:
            self.checkpoints.append(dict(state))
            print(f"\n[stream] >>> 进入节点: {current_node}")
            print(f"[stream] 当前 state: {state}")

            node_func = self.graph.nodes[current_node]
            if node_func:
                updates = node_func(state)
                print(f"[stream] 节点返回 updates: {updates}")
                if updates:
                    state.update(updates)
                    print(f"[stream] 合并后 state: {state}")

            print("[stream] 产出状态快照")
            yield dict(state)

            if current_node in self.graph.conditional_edges:
                condition, path_map = self.graph.conditional_edges[current_node]
                decision = condition(state)
                next_node = path_map.get(decision, END)
                print(f"[stream] 条件边决策: {decision} -> 下一节点: {next_node}")
            elif current_node in self.graph.edges:
                next_node = self.graph.edges.get(current_node, END)
                print(f"[stream] 普通边: {current_node} -> {next_node}")
            else:
                next_node = END
                print("[stream] 无出边，默认 -> END")

            current_node = next_node
        self.checkpoints.append(dict(state))
        print("\n[stream] 到达 END，最终状态快照")
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

    # TODO 8: 创建 StateGraph，添加 research / analyze / write 三个节点
    # 并设置入口为 research，连接 research -> analyze
    # analyze 通过条件边决定回到 research 还是前往 write
    # write -> END
    graph = StateGraph(dict)
    graph.add_node("research", research_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("write", write_node)
    graph.set_entry_point("research")
    graph.add_edge("research", "analyze")
    graph.add_conditional_edges(
        "analyze", decide_after_analyze, {"write": "write", "research": "research"}
    )
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
