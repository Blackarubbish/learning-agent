from typing import Any


class ToolManager:
    def __init__(self):
        self.tools: dict[str, dict[str, Any]] = {}

    def register_tool(self, name: str, desc: str, func: callable):
        self.tools[name] = {"name": name, "description": desc, "function": func}
        print(f"注册工具: {name}")

    def get_tool(self, name: str) -> callable:
        target = self.tools.get(name, {})
        if not target:
            return None
        return target.get("function")

    def get_available_tools(self) -> str:
        return "\n".join(f"- {name}: {info['description']}" for name, info in self.tools.items())
