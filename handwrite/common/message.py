from enum import StrEnum


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage:
    def __init__(self, role: Role, content: str, timestamp: float):
        self.role = role
        self.content = content
        self.timestamp = timestamp

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}
    
    def to_str(self) -> str:
        return f"[{self.role}]: {self.content}"


def create_msg(role: Role, content: str) -> LLMMessage:
    import time

    return LLMMessage(role=role, content=content, timestamp=time.time())
