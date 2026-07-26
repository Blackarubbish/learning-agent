"""Hello-Agents practice utilities."""

import os

from dotenv import load_dotenv


def load_env_if_needed() -> None:
    """Load environment variables from .env if present."""
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    elif os.path.exists(".env"):
        load_dotenv(".env")
