"""Load Kimi configuration without exposing secrets or calling the network."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_KIMI_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_KIMI_MODEL = "kimi-k2.6"
DEFAULT_LANGSMITH_PROJECT = "business-analysis-langgraph-interview-repro"


@dataclass(frozen=True)
class KimiSettings:
    api_key: str | None
    base_url: str
    model_name: str


@dataclass(frozen=True)
class LangSmithSettings:
    tracing_enabled: bool
    api_key: str | None
    project_name: str


def load_project_environment() -> None:
    """Load project configuration, then optionally load a referenced local secret file."""
    load_dotenv(PROJECT_DIR / ".env", override=False)

    referenced_env = os.getenv("MOONSHOT_ENV_FILE")
    if not referenced_env:
        return

    referenced_path = Path(referenced_env).expanduser()
    if not referenced_path.is_file():
        raise RuntimeError(f"MOONSHOT_ENV_FILE does not exist: {referenced_path}")
    load_dotenv(referenced_path, override=False)


def get_kimi_settings(*, load_env: bool = True, require_api_key: bool = True) -> KimiSettings:
    if load_env:
        load_project_environment()

    settings = KimiSettings(
        api_key=os.getenv("MOONSHOT_API_KEY"),
        base_url=os.getenv("MOONSHOT_BASE_URL", DEFAULT_KIMI_BASE_URL),
        model_name=os.getenv("MODEL_NAME", DEFAULT_KIMI_MODEL),
    )
    if require_api_key and not settings.api_key:
        raise RuntimeError(
            "MOONSHOT_API_KEY is missing. Put it in an ignored local env file; "
            "never hard-code it or paste it into chat."
        )
    return settings


def get_langsmith_settings(*, load_env: bool = True) -> LangSmithSettings:
    if load_env:
        load_project_environment()

    tracing_value = os.getenv("LANGSMITH_TRACING", "false").strip().lower()
    return LangSmithSettings(
        tracing_enabled=tracing_value in {"1", "true", "yes", "on"},
        api_key=os.getenv("LANGSMITH_API_KEY"),
        project_name=os.getenv("LANGSMITH_PROJECT", DEFAULT_LANGSMITH_PROJECT),
    )


def ensure_langsmith_ready() -> LangSmithSettings:
    """Fail before a paid model call if tracing is enabled but cannot authenticate."""
    settings = get_langsmith_settings()
    if settings.tracing_enabled and not settings.api_key:
        raise RuntimeError(
            "LANGSMITH_TRACING is enabled, but LANGSMITH_API_KEY is missing. "
            "Create a LangSmith API key, save it in the ignored .env, and retry."
        )
    return settings


def create_kimi_model() -> ChatOpenAI:
    """Create a non-thinking Kimi K2.6 chat model for the first Tool Calling lab."""
    settings = get_kimi_settings()
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=120,
        max_retries=2,
        extra_body={"thinking": {"type": "disabled"}},
    )


def main() -> None:
    settings = get_kimi_settings()
    langsmith_settings = get_langsmith_settings(load_env=False)
    print("provider: kimi")
    print(f"model: {settings.model_name}")
    print(f"base_url: {settings.base_url}")
    print(f"api_key: {'present' if settings.api_key else 'missing'}")
    print(f"langsmith_tracing: {str(langsmith_settings.tracing_enabled).lower()}")
    print(f"langsmith_api_key: {'present' if langsmith_settings.api_key else 'missing'}")
    print(f"langsmith_project: {langsmith_settings.project_name}")


if __name__ == "__main__":
    main()
