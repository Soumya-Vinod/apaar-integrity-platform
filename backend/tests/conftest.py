# Owner: Dev B
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def settings_override():
    """Temporarily change cached settings, e.g. settings_override(mock_mode=False)."""
    settings = get_settings()
    saved = settings.model_dump()

    def apply(**values):
        for key, value in values.items():
            setattr(settings, key, value)

    yield apply
    for key, value in saved.items():
        setattr(settings, key, value)


def as_role(role: str, institution: str | None = None) -> dict[str, str]:
    headers = {"X-Demo-Role": role}
    if institution:
        headers["X-Demo-Institution"] = institution
    return headers
