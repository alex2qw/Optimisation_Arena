import pytest

from app.config import get_settings


@pytest.fixture
def offline_settings():
    return get_settings().model_copy(update={"openai_api_key": "", "openai_insights_enabled": False})


@pytest.fixture(autouse=True)
def disable_network_ai_for_api_tests(monkeypatch):
    settings = get_settings().model_copy(update={"openai_api_key": "", "openai_insights_enabled": False})
    monkeypatch.setattr("app.api.experiments.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.insights.get_settings", lambda: settings)
