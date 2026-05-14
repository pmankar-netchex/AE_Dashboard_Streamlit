from __future__ import annotations

import pytest

from app.services.user_service import UserRow, get_user_service


@pytest.fixture(autouse=True)
def _no_azure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    from app.config import get_settings

    get_settings.cache_clear()
    get_user_service.cache_clear()


def test_get_returns_none_for_missing() -> None:
    assert get_user_service().get("missing@example.com") is None


def test_upsert_then_get_normalizes_email_case() -> None:
    svc = get_user_service()
    svc.upsert(UserRow(email="UPPER@example.com", role="admin"), actor="seed")
    row = svc.get("upper@example.com")
    assert row is not None
    assert row.email == "upper@example.com"
    assert row.role == "admin"
    assert row.is_active is True


def test_upsert_preserves_added_by_and_added_at_on_update() -> None:
    svc = get_user_service()
    svc.upsert(UserRow(email="x@example.com", role="user"), actor="first")
    original = svc.get("x@example.com")
    assert original is not None
    svc.upsert(UserRow(email="x@example.com", role="admin"), actor="second")
    after = svc.get("x@example.com")
    assert after is not None
    assert after.role == "admin"
    assert after.added_by == original.added_by  # not overwritten
    assert after.added_at == original.added_at


def test_list_returns_sorted_by_email() -> None:
    svc = get_user_service()
    for e in ["c@x", "a@x", "b@x"]:
        svc.upsert(UserRow(email=e, role="user"), actor="seed")
    emails = [u.email for u in svc.list()]
    assert emails == ["a@x", "b@x", "c@x"]


def test_delete_returns_false_for_missing() -> None:
    assert get_user_service().delete("nope@example.com", "t") is False


def test_delete_removes_existing() -> None:
    svc = get_user_service()
    svc.upsert(UserRow(email="goner@example.com", role="user"), actor="t")
    assert svc.delete("goner@example.com", "t") is True
    assert svc.get("goner@example.com") is None
