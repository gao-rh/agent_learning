import pytest

from business_analysis_repro.settings import (
    DEFAULT_KIMI_BASE_URL,
    DEFAULT_KIMI_MODEL,
    ensure_langsmith_ready,
    get_kimi_settings,
)
from business_analysis_repro.smoke import run_smoke


def test_langgraph_environment_smoke() -> None:
    assert run_smoke() == {"value": 1, "events": ["environment_ready"]}


def test_kimi_settings_defaults_without_loading_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_BASE_URL", raising=False)
    monkeypatch.delenv("MODEL_NAME", raising=False)

    settings = get_kimi_settings(load_env=False, require_api_key=False)

    assert settings.api_key is None
    assert settings.base_url == DEFAULT_KIMI_BASE_URL
    assert settings.model_name == DEFAULT_KIMI_MODEL


def test_kimi_settings_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="MOONSHOT_API_KEY is missing"):
        get_kimi_settings(load_env=False)


def test_langsmith_requires_key_only_when_tracing_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setattr(
        "business_analysis_repro.settings.load_project_environment",
        lambda: None,
    )

    with pytest.raises(RuntimeError, match="LANGSMITH_API_KEY is missing"):
        ensure_langsmith_ready()
