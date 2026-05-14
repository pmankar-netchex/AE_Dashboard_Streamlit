from __future__ import annotations

import base64
import json

from app.auth.principal import parse_x_ms_client_principal


def _encode(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def test_returns_none_for_missing() -> None:
    assert parse_x_ms_client_principal(None) is None
    assert parse_x_ms_client_principal("") is None


def test_returns_none_for_malformed() -> None:
    assert parse_x_ms_client_principal("!!!not-base64!!!") is None


def test_extracts_email_from_preferred_username() -> None:
    payload = {
        "claims": [
            {"typ": "preferred_username", "val": "Sarah.Khan@netchex.com"},
            {"typ": "oid", "val": "abc-123"},
        ],
        "identityProvider": "aad",
    }
    result = parse_x_ms_client_principal(_encode(payload))
    assert result is not None
    assert result["email"] == "sarah.khan@netchex.com"
    assert result["oid"] == "abc-123"


def test_extracts_email_from_xmlsoap_claim() -> None:
    payload = {
        "claims": [
            {
                "typ": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                "val": "user@example.com",
            }
        ]
    }
    result = parse_x_ms_client_principal(_encode(payload))
    assert result is not None
    assert result["email"] == "user@example.com"


def test_returns_none_when_no_email_claim() -> None:
    payload = {"claims": [{"typ": "name", "val": "Anon"}]}
    assert parse_x_ms_client_principal(_encode(payload)) is None
