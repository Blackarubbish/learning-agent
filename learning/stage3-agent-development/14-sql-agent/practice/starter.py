"""
SQL 工具开发：让 Agent 操作数据库

目标：构建面向 Agent 的 SQL 工具，结合第 13 章的信息抽象原则。

核心认知（开始前读）：
  - Agent + 数据库 = 强大的交互式查询能力：用户用自然语言，Agent 转 SQL 探索
  - 安全第一：Agent 绝不能执行 DROP/DELETE/INSERT/UPDATE
  - 结果必须限流：SELECT * 可能返回百万行，Agent 只需要前 N 行 + 总数
  - Schema 探索是独立工具：让 Agent 先"看目录"，再"翻书"

运行：
  make run f=learning/stage3-agent-development/14-sql-agent/practice/starter.py
"""

import json
import re
import sqlite3

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()
llm = get_or_create_llm(temperature=0)

# ═══════════════════════════════════════════
# Mock 数据库：电商平台
# ═══════════════════════════════════════════


def create_mock_db() -> sqlite3.Connection:
    """创建内存 SQLite 数据库并填充示例数据"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT '普通'
        )
    """)
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)

    products = [
        (1, "机械键盘 K100", "电子产品", 399.00, 120),
        (2, "27寸 4K显示器", "电子产品", 2499.00, 35),
        (3, "Python 编程入门", "图书", 59.00, 200),
        (4, "深度强化学习", "图书", 89.00, 80),
        (5, "人体工学椅", "办公家具", 1599.00, 15),
        (6, "无线降噪耳机", "电子产品", 699.00, 60),
        (7, "Type-C 扩展坞", "电子产品", 199.00, 150),
        (8, "机器学习实战", "图书", 79.00, 95),
        (9, "升降桌", "办公家具", 2199.00, 10),
        (10, "机械键盘 K200", "电子产品", 499.00, 85),
    ]
    cursor.executemany("INSERT INTO products (id, name, category, price, stock) VALUES (?, ?, ?, ?, ?)", products)

    customers = [
        (1, "张三", "北京", "VIP"),
        (2, "李四", "上海", "普通"),
        (3, "王五", "深圳", "VIP"),
        (4, "赵六", "北京", "普通"),
        (5, "钱七", "杭州", "普通"),
        (6, "孙八", "上海", "VIP"),
        (7, "周九", "广州", "普通"),
        (8, "吴十", "深圳", "普通"),
    ]
    cursor.executemany("INSERT INTO customers (id, name, city, level) VALUES (?, ?, ?, ?)", customers)

    orders = [
        (1, 1, 1, 2, "2026-05-01", "completed"),
        (2, 1, 3, 1, "2026-05-02", "completed"),
        (3, 2, 2, 1, "2026-05-03", "shipped"),
        (4, 3, 6, 3, "2026-05-04", "completed"),
        (5, 4, 1, 1, "2026-05-05", "pending"),
        (6, 5, 5, 2, "2026-05-06", "completed"),
        (7, 6, 2, 1, "2026-05-07", "completed"),
        (8, 2, 4, 2, "2026-05-08", "shipped"),
        (9, 7, 8, 1, "2026-05-09", "completed"),
        (10, 3, 9, 1, "2026-05-10", "pending"),
        (11, 8, 7, 2, "2026-05-11", "completed"),
        (12, 1, 10, 1, "2026-05-12", "pending"),
        (13, 6, 3, 3, "2026-05-12", "completed"),
        (14, 4, 6, 1, "2026-05-13", "shipped"),
        (15, 5, 8, 1, "2026-05-13", "pending"),
    ]
    cursor.executemany(
        "INSERT INTO orders (id, customer_id, product_id, quantity, date, status) VALUES (?, ?, ?, ?, ?, ?)",
        orders,
    )

    conn.commit()
    return conn


db = create_mock_db()

# ═══════════════════════════════════════════
# TODO 1: Schema 探索工具 — 让 Agent 先"看目录"
# ═══════════════════════════════════════════
# Agent 不懂数据库结构，需要一个工具来探索 schema。
# 类比：去图书馆先查目录，而非随机翻书架。
#
# sqlite3 提示：
#   - 查所有表: SELECT name FROM sqlite_master WHERE type='table'
#   - 查表结构: PRAGMA table_info('表名')  → 返回每列的 cid, name, type, notnull, dflt_value, pk


def db_schema(table_name: str = "") -> str:
    """查看数据库表结构。

    TODO 1: 实现 schema 探索

    1. 不传参数时: 查询 sqlite_master 获取所有表名，返回表名列表
       格式: "📋 数据库包含 N 张表: products, customers, orders\n使用 db_schema('<表名>') 查看表结构"


    2. 传表名时: 用 PRAGMA table_info 获取列信息（name, type），格式化输出
       格式: "📋 表 'XXX' 结构 (N 列):\n  id (INTEGER)\n  name (TEXT)\n  ..."

    3. 表名不存在时: 返回友好提示，列出可用表名
    """
    # TODO: 实现 schema 探索
    if not table_name:
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        return f"📋 数据库包含 {len(tables)} 张表: {', '.join(tables)}\n使用 db_schema('<表名>') 查看表结构"
    else:
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor.fetchall()]
            return f"⛔ 表 '{table_name}' 不存在。可用表: {', '.join(tables)}"
        cursor = db.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()
        col_info = "\n  ".join(f"{col['name']} ({col['type']})" for col in columns)
        return f"📋 表 '{table_name}' 结构 ({len(columns)} 列):\n  {col_info}"


# ═══════════════════════════════════════════
# TODO 2: SQL 查询工具 — 安全 + 限流
# ═══════════════════════════════════════════


def db_query(sql: str, max_rows: int = 10) -> str:
    """执行只读 SQL 查询，返回结构化结果。

    TODO 2: 实现安全的 SQL 查询工具

    1. 安全校验（sqlite3 是本地数据库，安全重点是防止 LLM 生成破坏性 SQL）:
       - 禁止 INSERT / UPDATE / DELETE / DROP / ALTER / CREATE
       - 提示: 用正则 \b{keyword}\b 匹配独立单词
       - 拦截时返回 "⛔ 安全限制：禁止执行 {keyword} 操作。此工具仅支持只读查询 (SELECT)。"

    2. 执行查询:
       - 如果 SQL 中不含 LIMIT，自动追加 "LIMIT {max_rows + 1}"
       - 用 cursor.execute 执行，cursor.fetchall() 获取结果
       - cursor.description 获取列名列表

    3. 格式化输出（信息抽象，同第 13 章模式）:
       格式: "📊 查询结果: N 行, M 列\n   列: col1, col2, ...\n  [1] col1=val1, col2=val2\n  ..."
       - 最多显示 max_rows 行
       - 如果有更多行（len(rows) > max_rows），提示截断并给出缩小范围的建议

    4. SQL 执行错误时:
       - 返回错误信息 + 建议用 db_schema 确认列名
    """
    # TODO: 实现 SQL 查询
    if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b", sql, re.IGNORECASE):
        keyword = re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b", sql, re.IGNORECASE).group(0)
        return f"⛔ 安全限制：禁止执行 {keyword} 操作。此工具仅支持只读查询 (SELECT)。"

    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql += f" LIMIT {max_rows + 1}"

    try:
        cursor = db.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            return "📊 查询结果: 0 行, 0 列"

        col_names = [desc[0] for desc in cursor.description]
        result_lines = [f"📊 查询结果: {len(rows)} 行, {len(col_names)} 列", f"   列: {', '.join(col_names)}"]
        for i, row in enumerate(rows[:max_rows], start=1):
            values = ", ".join(f"{col}={val}" for col, val in zip(col_names, row, strict=True))
            result_lines.append(f"  [{i}] {values}")

        if len(rows) > max_rows:
            result_lines.append(f"⚠️ 结果被截断。显示前 {max_rows} 行，共 {len(rows)} 行。建议缩小查询范围。")

        return "\n".join(result_lines)
    except sqlite3.Error as e:
        return f"❌ 查询错误: {e}\n💡 建议: 使用 db_schema 确认列名和表结构"


# ═══════════════════════════════════════════
# 3. 工具注册（已提供）
# ═══════════════════════════════════════════

TOOLS = {
    "db_schema": {
        "function": db_schema,
        "schema": {
            "description": "查看数据库结构。不传参数列出所有表，传入表名查看该表的列信息（列名+类型）",
            "parameters": {"table_name": "要查看的表名，留空列出所有表"},
        },
    },
    "db_query": {
        "function": db_query,
        "schema": {
            "description": "执行只读 SQL 查询（仅支持 SELECT）。自动限制返回行数，超出时提示缩小范围。查询前建议先用 db_schema 了解表结构",
            "parameters": {
                "sql": "SQL SELECT 查询语句, 如 'SELECT name, price FROM products WHERE category=\"电子产品\"'",
                "max_rows": "最多返回行数，默认 10",
            },
        },
    },
}


# ═══════════════════════════════════════════
# 4. Agent（复用第 12 章的 ReAct 循环，已提供）
# ═══════════════════════════════════════════


def build_tool_descriptions(tools: dict) -> str:
    lines = []
    for name, info in tools.items():
        schema = info["schema"]
        params = ", ".join(f"{k}: {v}" for k, v in schema["parameters"].items())
        lines.append(f"- **{name}**: {schema['description']}\n  参数: {params}")
    return "\n".join(lines)


REACT_PROMPT = """你是一个智能 Agent，具有推理和行动能力。你可以使用工具来完成任务。

## 可用工具

{tool_descriptions}

## 输出格式

你必须严格按照以下格式输出。每次只输出一个 Thought 加上一个 Action 或一个 Final Answer。

**调用工具时：**
Thought: <你的推理过程>
Action: <工具名称，必须是 {tool_names} 之一>
Action Input: <JSON 格式的参数，key 必须和工具定义一致>

**得到最终答案时：**
Thought: 我现在已经收集到足够的信息来回答问题
Final Answer: <简洁的最终答案>

注意：
- Action Input 必须是合法的 JSON 对象
- 一次只能调用一个工具
- 如果工具返回了结果，你需要基于结果继续推理
- 如果工具调用失败或返回错误，尝试其他方式或如实告知用户"""


def parse_react_output(text: str) -> dict:
    """解析 LLM 的 ReAct 格式输出，使用括号计数提取 JSON"""
    text = text.strip()

    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return {"type": "final_answer", "answer": final_match.group(1).strip()}

    action_match = re.search(r"Action:\s*(\S+)", text, re.IGNORECASE)
    input_start = text.find("Action Input:")
    if action_match and input_start != -1:
        tool_name = action_match.group(1).strip()
        rest = text[input_start:]
        brace_start = rest.find("{")
        if brace_start == -1:
            return {"type": "parse_error", "raw": text, "reason": "Action Input 后未找到 JSON"}

        depth = 0
        brace_end = -1
        for i in range(brace_start, len(rest)):
            if rest[i] == "{":
                depth += 1
            elif rest[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break

        if brace_end == -1:
            return {"type": "parse_error", "raw": text, "reason": "JSON 括号不匹配"}

        json_str = rest[brace_start : brace_end + 1]
        try:
            tool_input = json.loads(json_str)
        except json.JSONDecodeError:
            return {"type": "parse_error", "raw": text, "reason": "Action Input 不是合法 JSON"}
        return {"type": "action", "tool": tool_name, "input": tool_input}

    return {"type": "parse_error", "raw": text, "reason": "无法识别输出格式"}


class Agent:
    """ReAct Agent 执行器"""

    def __init__(self, llm, tools: dict):
        self.llm = llm
        self.tools = tools

    def run(self, user_question: str, max_steps: int = 8) -> dict:
        tool_descriptions = build_tool_descriptions(self.tools)
        tool_names = list(self.tools.keys())

        system_prompt = REACT_PROMPT.format(tool_descriptions=tool_descriptions, tool_names="/".join(tool_names))

        messages = [{"role": "system", "content": system_prompt}]
        steps = []

        for step_idx in range(max_steps):
            if step_idx == 0:
                messages.append({"role": "user", "content": user_question})
            else:
                last_step = steps[-1]
                messages.append(
                    {
                        "role": "user",
                        "content": f"Observation: {last_step['result']}",
                    }
                )

            parts = []
            for m in messages:
                label = {"system": "System", "user": "Human", "assistant": "AI"}[m["role"]]
                parts.append(f"{label}: {m['content']}")
            full_prompt = "\n\n".join(parts)

            response = self.llm.invoke(full_prompt)
            llm_output = response.content if hasattr(response, "content") else str(response)
            parsed = parse_react_output(llm_output)

            if parsed["type"] == "final_answer":
                steps.append({"thought": llm_output, "type": "final"})
                return {"answer": parsed["answer"], "steps": steps}

            elif parsed["type"] == "action":
                tool_name = parsed["tool"]
                tool_input = parsed["input"]

                if tool_name not in self.tools:
                    observation = f"错误: 没有名为 '{tool_name}' 的工具，可用工具: {tool_names}"
                else:
                    try:
                        tool_func = self.tools[tool_name]["function"]
                        observation = tool_func(**tool_input)
                    except TypeError as e:
                        observation = f"工具参数错误: {e}。请检查参数名称和类型是否与工具定义一致"
                    except Exception as e:
                        observation = f"工具执行失败: {e}"

                steps.append(
                    {
                        "thought": llm_output,
                        "type": "action",
                        "tool": tool_name,
                        "input": tool_input,
                        "result": observation,
                    }
                )
            else:
                error_msg = f"格式错误 ({parsed.get('reason', '未知')})。请严格按照 Thought/Action/Action Input 或 Thought/Final Answer 格式输出。"
                steps.append(
                    {
                        "thought": llm_output,
                        "type": "parse_error",
                        "result": error_msg,
                    }
                )

        last_output = steps[-1].get("thought", "") if steps else ""
        if steps and steps[-1]["type"] == "action" and "错误" not in steps[-1].get("result", ""):
            return {"answer": steps[-1]["result"], "steps": steps}
        return {
            "answer": f"Agent 在 {max_steps} 步内未能得出最终答案。最后状态: {last_output[:200]}",
            "steps": steps,
        }


# ═══════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════
if __name__ == "__main__":
    reset()

    # ── 1. Schema 探索 ──
    section("1. Schema 探索")
    all_tables = db_schema()
    print(f"所有表: {all_tables}")
    check(
        "列出所有表",
        "products" in all_tables and "customers" in all_tables and "orders" in all_tables,
    )

    products_schema = db_schema("products")
    print(f"\nproducts 表结构:\n{products_schema}")
    check("products 包含列信息", "id" in products_schema and "price" in products_schema)

    bad_table = db_schema("nonexistent")
    print(f"\n不存在的表:\n{bad_table}")
    check("不存在的表给出提示", "不存在" in bad_table or "可用表" in bad_table)

    # ── 2. SQL 安全校验 ──
    section("2. SQL 安全校验")
    dangerous = db_query("DELETE FROM products WHERE price < 100")
    print(f"危险操作拦截:\n{dangerous}")
    check("拦截 DELETE", "禁止" in dangerous or "安全" in dangerous)

    non_select = db_query("CREATE TABLE test (id INT)")
    print(f"\n非 SELECT 拦截:\n{non_select}")
    check("拦截非 SELECT", "仅支持" in non_select)

    # ── 3. SQL 查询（正常查询 + 信息抽象） ──
    section("3. SQL 查询")
    result = db_query("SELECT name, price, stock FROM products ORDER BY price DESC")
    print(f"产品查询:\n{result}")
    check("包含列名", "name" in result and "price" in result)
    check("最多返回 10 行", result.count("[") <= 10)

    # 聚合查询
    count_result = db_query("SELECT category, COUNT(*) as cnt FROM products GROUP BY category")
    print(f"分类统计:\n{count_result}")
    check("聚合查询成功", "cnt" in count_result or "count" in count_result.lower())

    # 错误列名
    wrong_column = db_query("SELECT wrong_column FROM products")
    print(f"错误列名:\n{wrong_column[:200]}")
    check("SQL 错误给出修复建议", "建议" in wrong_column or "db_schema" in wrong_column)

    # ── 4. Agent 集成：自然语言到 SQL ──
    section("4. Agent 集成：自然语言查询")
    agent = Agent(llm, TOOLS)

    result = agent.run("数据库里有哪些表？每张表有什么字段？")
    print("问题: 数据库里有哪些表？每张表有什么字段？")
    print(f"步骤数: {len(result['steps'])}")
    for i, s in enumerate(result["steps"]):
        if s["type"] == "action":
            print(f"  步骤 {i + 1}: {s['tool']} → {s['result'][:100]}")
    print(f"答案: {result['answer'][:300]}")
    check("Agent 探索了 schema", any("schema" in s.get("tool", "") for s in result["steps"]))

    # ── 5. Agent 复杂查询 ──
    section("5. Agent 复杂查询")
    result = agent.run("电子产品中价格最高的 3 款是什么？总共有多少电子产品订单？")
    print("问题: 电子产品中价格最高的 3 款是什么？总共有多少电子产品订单？")
    print(f"步骤数: {len(result['steps'])}")
    for i, s in enumerate(result["steps"]):
        if s["type"] == "action":
            print(f"  步骤 {i + 1}: {s['tool']} → {s['result'][:150]}")
    print(f"答案: {result['answer']}")
    check("Agent 能回答复杂查询", len(result["answer"]) > 0)

    summary()
