from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def dev_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("DEV_ROLE", "admin")
    monkeypatch.setenv("DEV_USER_EMAIL", "test@example.com")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    # Force fresh settings each test
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())
