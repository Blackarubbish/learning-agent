"""Chapter 6: First AgentScope example.

Run with: uv run --directory practice python examples/chapter6_agentscope/hello_agentscope.py
"""

from hello_agents_practice import load_env_if_needed

load_env_if_needed()


def main() -> None:
    import agentscope

    print(f"AgentScope version: {agentscope.__version__}")
    print("AgentScope is ready!")


if __name__ == "__main__":
    main()
