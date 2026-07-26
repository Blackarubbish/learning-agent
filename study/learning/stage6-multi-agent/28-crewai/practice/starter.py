"""
第 28 章 — CrewAI 角色驱动的任务协作（手动版）

目标：实现一个极简 CrewAI，理解：
- Agent: role + goal + backstory 三段式角色定义
- Task: description + expected_output + agent + context 任务定义
- Crew: agents + tasks + process 编排容器
- Process: sequential 顺序执行 vs hierarchical 经理协调执行
"""

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)


class Agent:
    """CrewAI 风格 Agent：用角色、目标、背景故事定义行为。"""

    def __init__(self, role: str, goal: str, backstory: str) -> None:
        self.role = role
        self.goal = goal
        self.backstory = backstory

    def run(self, task_description: str, context: str = "") -> str:
        """
        根据角色定义和上下文生成任务输出。

        Args:
            task_description: 当前任务的描述
            context: 来自前置任务的上下文（可能为空）
        """
        system_prompt = (
            f"你是 {self.role}。\n"
            f"你的目标：{self.goal}\n"
            f"你的背景：{self.backstory}\n"
            "请严格扮演这个角色，不要跳出角色。输出简洁、专业。"
        )

        user_prompt = (
            f"前置上下文：\n{context}\n\n当前任务：{task_description}"
            if context
            else task_description
        )

        # TODO 1: 调用 llm 生成回复，返回 content
        response = llm.invoke([SystemMessage(system_prompt), HumanMessage(user_prompt)])
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
        """
        TODO 2: 把所有 context 任务的 description 和 output 拼接成一个字符串。

        格式示例：
        ---
        任务：收集资料
        输出：...
        ---
        任务：分析观点
        输出：...
        ---
        """
        result = "---\n"
        for ctx in self.context:
            result += f"任务:{ctx.description}\n输出:{ctx.output}---\n"
        return result


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
        """
        TODO 3: 顺序执行所有 tasks。

        规则：
        1. 按 self.tasks 列表顺序遍历
        2. 对每个 task 调用 _execute_task，order 从 1 开始递增
        3. 返回执行后的 tasks
        """
        result_tasks: list[Task] = []
        for order, task in enumerate(self.tasks, 1):
            self._execute_task(task, order)
            result_tasks.append(task)
        return result_tasks

    def _run_hierarchical(self) -> list[Task]:
        """
        TODO 4: 层级执行流程。

        规则：
        1. 用 self.manager 生成一个执行计划（返回任务索引列表，如 "1,2,3"）
        2. 解析计划得到 ordered_indices
        3. 按 ordered_indices 顺序执行对应 task
        4. 返回执行后的 tasks

        提示：manager prompt 中应包含每个 task 的 description 和 expected_output，
        要求其只返回用逗号分隔的索引数字，从 0 开始。
        """
        if self.manager is None:
            raise ValueError("hierarchical process 必须提供 manager Agent")

        plan_prompt = "你是项目协调员。以下是待执行的任务列表，请决定执行顺序。\n\n"
        for i, task in enumerate(self.tasks, 1):
            plan_prompt += f"[{i}] {task.description} | 期望输出：{task.expected_output}\n"
        plan_prompt += "\n只返回用逗号分隔的任务索引数字（如：1,2,3），不要解释。"

        plan = self.manager.run(plan_prompt)
        print(f"🧑‍💼 Manager 计划: {plan}")

        # TODO 4: 解析 plan 字符串，得到 ordered_indices，然后依次执行
        ordered_indices: list[int] = []
        for part in plan.split(","):
            clean_part = part.strip()
            if clean_part.isdigit():  # 过滤非数字内容（防止 LLM 不听话）
                idx = int(clean_part)
                if 0 < idx <= len(self.tasks):  # 边界检查
                    ordered_indices.append(idx)

        result_task: list[Task] = []
        for task_idx in ordered_indices:
            target_task = self.tasks[task_idx - 1]
            self._execute_task(target_task, task_idx)
            result_task.append(target_task)
        return result_task

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

    # TODO 5: 创建 sequential Crew 并运行
    crew_sequential = Crew(
        agents=[researcher, analyst, writer],
        tasks=[task_research, task_analyze, task_write],
        manager=manager,
        process="sequential",
    )
    results_seq = crew_sequential.run()

    check("Sequential 完成了 3 个任务", len(results_seq) == 3)
    check("Sequential 按顺序执行", [t.execution_order for t in results_seq] == [1, 2, 3])
    check("第二个任务依赖第一个任务的输出", task_research.output and task_analyze.output)

    section("测试 Hierarchical Process")

    # TODO 6: 创建 hierarchical Crew（带 manager）并运行
    crew_hierarchical = Crew(
        agents=[researcher, analyst, writer],
        tasks=[task_research, task_analyze, task_write],
        manager=manager,
        process="hierarchical",
    )
    results_hier = crew_hierarchical.run()

    check("Hierarchical 完成了 3 个任务", len(results_hier) == 3)
    check("Hierarchical 中所有任务都被执行", all(t.execution_order > 0 for t in results_hier))
    check("Hierarchical 三个 Agent 都参与了", len(set(t.agent.role for t in results_hier)) == 3)

    summary()
