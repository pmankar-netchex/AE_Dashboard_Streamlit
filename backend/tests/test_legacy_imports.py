"""Smoke tests for the ported legacy modules.

Verifies imports succeed, public surface is intact, and pure helpers work
end-to-end without Salesforce or Azure dependencies.
"""
from __future__ import annotations

from datetime import date

from app.legacy import data_engine, soql_registry, soql_store, time_filters


def test_soql_registry_exposes_all_columns() -> None:
    assert isinstance(soql_registry.ALL_COLUMNS, list)
    assert len(soql_registry.ALL_COLUMNS) > 30
    # Every column has a stable col_id and section
    for entry in soql_registry.ALL_COLUMNS:
        assert entry.col_id
        assert entry.section


def test_soql_registry_build_query_substitutes_owner_clause() -> None:
    entry = next(
        e for e in soql_registry.ALL_COLUMNS if not e.computed and not e.blocked
    )
    params = time_filters.build_filter_params(
        time_start=date(2026, 5, 1),
        time_end=date(2026, 5, 31),
        ae_user_id="005AAA000000000",
        ae_email="u@x",
        manager_name=None,
    )
    q = soql_registry.build_query(entry, params)
    assert isinstance(q, str)
    # Templates use placeholders like {owner_clause}; substitution must produce
    # output without raw curly-brace residue for resolved keys.
    assert "{owner_clause}" not in q
    assert "{ae_email_clause}" not in q


def test_data_engine_imports_without_salesforce() -> None:
    assert hasattr(data_engine, "build_dashboard_dataframe")
    assert hasattr(data_engine, "fetch_column")
    assert hasattr(data_engine, "get_managers_list")
    assert hasattr(data_engine, "clear_query_failures")
    # Idempotent
    data_engine.clear_query_failures()
    data_engine.clear_query_failures()


def test_time_filters_this_month_range() -> None:
    start, end = time_filters.this_month_range(today=date(2026, 5, 14))
    assert start == date(2026, 5, 1)
    assert end == date(2026, 5, 31)


def test_time_filters_last_month_range() -> None:
    start, end = time_filters.last_month_range(today=date(2026, 5, 14))
    assert start == date(2026, 4, 1)
    assert end == date(2026, 4, 30)


def test_time_filters_next_month_wraps_year() -> None:
    start, end = time_filters.next_month_range(today=date(2026, 12, 15))
    assert start == date(2027, 1, 1)
    assert end == date(2027, 1, 31)


def test_time_filters_resolve_custom() -> None:
    start, end = time_filters.resolve_time_period(
        "custom", custom_start=date(2026, 1, 1), custom_end=date(2026, 3, 31)
    )
    assert start == date(2026, 1, 1)
    assert end == date(2026, 3, 31)


def test_time_filters_build_filter_params_shape() -> None:
    params = time_filters.build_filter_params(
        time_start=date(2026, 5, 1),
        time_end=date(2026, 5, 31),
        manager_name="Alice",
    )
    assert params["time_start"] == "2026-05-01T00:00:00Z"
    assert params["time_end"] == "2026-05-31T23:59:59Z"
    assert params["manager_name"] == "Alice"
    assert "fiscal_year_start" in params


def test_soql_store_local_fallback(tmp_path, monkeypatch) -> None:
    """With no Azure conn string, save/load roundtrips through a local JSON file."""
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "")
    fake = tmp_path / "soql_overrides.json"
    monkeypatch.setattr(soql_store, "_LOCAL_FILE", fake)
    soql_store.save_query("S1-COL-X", "SELECT 1 FROM Account")
    assert soql_store.load_queries() == {"S1-COL-X": "SELECT 1 FROM Account"}


def test_soql_store_write_gate_blocks_when_azure_active(monkeypatch) -> None:
    """With a conn string set and ALLOW_PROD_QUERY_WRITES unset, writes raise."""
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "fake-conn-str")
    monkeypatch.delenv("ALLOW_PROD_QUERY_WRITES", raising=False)
    import pytest

    with pytest.raises(soql_store.SoqlWriteForbidden):
        soql_store.save_query("S1-COL-X", "SELECT 1 FROM Account")


def test_soql_store_write_gate_allows_when_flag_set(monkeypatch) -> None:
    """With flag=true, the write proceeds (and will then fail at table client
    construction since the conn string is fake — which is the desired behavior:
    the gate doesn't reject, the storage layer does)."""
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "fake-conn-str")
    monkeypatch.setenv("ALLOW_PROD_QUERY_WRITES", "true")
    # Reset storage cache so the fake conn string is picked up
    from app.storage.tables import reset_service_cache
    from app.config import get_settings

    get_settings.cache_clear()
    reset_service_cache()
    # Should not raise SoqlWriteForbidden. Underlying azure call will fail,
    # but that's a separate failure mode we ignore here.
    try:
        soql_store.save_query("S1-COL-X", "SELECT 1 FROM Account")
    except soql_store.SoqlWriteForbidden:
        raise AssertionError("gate should be open when ALLOW_PROD_QUERY_WRITES=true")
    except Exception:
        # Expected — fake conn string can't reach a real table.
        pass
