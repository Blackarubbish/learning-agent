"""
第 28 章 — CrewAI 角色驱动的任务协作（手动版）

参考实现。重点不是复刻 CrewAI 框架，而是把「角色定义 → 任务描述 → 流程编排」
这三层抽象用最小代码表达出来。
"""

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


class Agent:
    """CrewAI 风格 Agent：用角色、目标、背景故事定义行为。"""

    def __init__(self, role: str, goal: str, backstory: str) -> None:
        self.role = role
        self.goal = goal
        self.backstory = backstory

    def run(self, task_description: str, context: str = "") -> str:
        """把角色定义注入 system prompt，再拼接任务与上下文。"""
        system_prompt = f"""你是 {self.role}。
你的目标：{self.goal}
你的背景：{self.backstory}
请严格扮演这个角色，不要跳出角色。输出简洁、专业。"""

        user_prompt = task_description
        if context:
            user_prompt = f"前置上下文：\n{context}\n\n当前任务：{task_description}"

        response = llm.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return response.content


class Task:
    """CrewAI 风格 Task：描述任务、期望输出、负责 Agent、依赖任务。"""

    def __init__(
        self,
        description: str,
        expected_output: str,
        agent: Agent,
        context: list["Task"] | None = None,
    ) -> None:
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.context = context or []
        self.output: str = ""
        self.execution_order: int = -1

    def get_context_string(self) -> str:
        """把前置任务的交付物拼接成上下文，供当前 Agent 参考。"""
        parts = []
        for task in self.context:
            parts.append(f"---\n任务：{task.description}\n输出：{task.output}\n---")
        return "\n".join(parts)


class Crew:
    """CrewAI 风格 Crew：把 Agents 和 Tasks 按 Process 编排执行。"""

    def __init__(
        self,
        agents: list[Agent],
        tasks: list[Task],
        process: str = "sequential",
        manager: Agent | None = None,
    ) -> None:
        self.agents = agents
        self.tasks = tasks
        self.process = process
        self.manager = manager

    def _execute_task(self, task: Task, order: int) -> None:
        """执行单个任务并记录结果。"""
        context = task.get_context_string()
        task.output = task.agent.run(task.description, context)
        task.execution_order = order
        print(f"  [{order}] {task.agent.role}: {task.output[:80]}...")

    def _run_sequential(self) -> list[Task]:
        """按 tasks 列表顺序执行，天然保证依赖顺序。"""
        print("🚀 启动 Sequential Process")
        for order, task in enumerate(self.tasks, start=1):
            self._execute_task(task, order)
        return self.tasks

    def _run_hierarchical(self) -> list[Task]:
        """由 manager 决定执行顺序，再按该顺序执行。"""
        if self.manager is None:
            raise ValueError("hierarchical process 必须提供 manager Agent")

        plan_prompt = "你是项目协调员。以下是待执行的任务列表，请决定执行顺序。\n\n"
        for i, task in enumerate(self.tasks):
            plan_prompt += f"[{i}] {task.description} | 期望输出：{task.expected_output}\n"
        plan_prompt += "\n只返回用逗号分隔的任务索引数字（如：0,1,2），不要解释。"

        plan = self.manager.run(plan_prompt)
        print(f"🧑‍💼 Manager 计划: {plan}")

        # 简单解析：去掉非数字和逗号字符，按逗号分割
        cleaned = "".join(char for char in plan if char.isdigit() or char == ",")
        ordered_indices = [int(x) for x in cleaned.split(",") if x.strip() != ""]

        # 安全兜底：如果解析失败或索引不合法，就按原顺序执行
        valid_indices = [i for i in ordered_indices if 0 <= i < len(self.tasks)]
        if len(valid_indices) != len(self.tasks):
            print("⚠️ Manager 计划解析异常，回退到默认顺序")
            valid_indices = list(range(len(self.tasks)))

        print("🚀 启动 Hierarchical Process，执行顺序:", valid_indices)
        for order, idx in enumerate(valid_indices, start=1):
            self._execute_task(self.tasks[idx], order)
        return self.tasks

    def run(self) -> list[Task]:
        """根据 process 类型分发执行。"""
        if self.process == "sequential":
            return self._run_sequential()
        if self.process == "hierarchical":
            return self._run_hierarchical()
        raise ValueError(f"不支持的 process: {self.process}")


if __name__ == "__main__":
    reset()

    section("定义角色")

    researcher = Agent(
        role="研究员",
        goal="收集与主题相关的事实和背景信息",
        backstory="你是一位资深行业研究员，擅长从海量信息中筛选可靠事实，从不加入个人推断。",
    )
    analyst = Agent(
        role="分析师",
        goal="基于事实提炼关键洞察和观点",
        backstory="你是一位数据分析师，习惯从研究员提供的事实中找出模式和趋势。",
    )
    writer = Agent(
        role="写手",
        goal="把洞察整理成一段流畅的总结",
        backstory="你是一位技术写作专家，擅长把复杂信息浓缩成易读的段落。",
    )
    manager = Agent(
        role="项目经理",
        goal="协调任务执行顺序，确保依赖关系正确",
        backstory="你是一位经验丰富的项目经理，只做计划不做具体执行。",
    )

    section("测试 Sequential Process")

    task_research = Task(
        description="请用 2-3 句话介绍 RAG 是什么",
        expected_output="一段关于 RAG 的定义",
        agent=researcher,
    )
    task_analyze = Task(
        description="基于研究员的资料，提炼 RAG 相比传统 LLM 的两个核心优势",
        expected_output="两个核心优势",
        agent=analyst,
        context=[task_research],
    )
    task_write = Task(
        description="基于以上洞察，写一段 100 字以内的总结",
        expected_output="一段总结文字",
        agent=writer,
        context=[task_research, task_analyze],
    )

    crew_sequential = Crew(
        agents=[researcher, analyst, writer],
        tasks=[task_research, task_analyze, task_write],
        process="sequential",
    )
    results_seq = crew_sequential.run()

    check("Sequential 完成了 3 个任务", len(results_seq) == 3)
    check("Sequential 按顺序执行", [t.execution_order for t in results_seq] == [1, 2, 3])
    check("第二个任务依赖第一个任务的输出", task_research.output and task_analyze.output)

    section("测试 Hierarchical Process")

    crew_hierarchical = Crew(
        agents=[researcher, analyst, writer, manager],
        tasks=[task_research, task_analyze, task_write],
        process="hierarchical",
        manager=manager,
    )
    results_hier = crew_hierarchical.run()

    check("Hierarchical 完成了 3 个任务", len(results_hier) == 3)
    check("Hierarchical 中所有任务都被执行", all(t.execution_order > 0 for t in results_hier))
    check("Hierarchical 三个 Agent 都参与了", len(set(t.agent.role for t in results_hier)) == 3)

    summary()
