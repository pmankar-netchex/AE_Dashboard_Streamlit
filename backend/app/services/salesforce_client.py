"""Salesforce client-credentials flow + thin SfClient wrapper.

Replaces the Web Server OAuth flow in legacy src/salesforce_oauth.py. The app
authenticates as a single integration identity; per-user Salesforce login is
gone. All data access happens through one shared token cached at module level.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Conservative lifetime — Salesforce CC flow doesn't return expires_in.
# 401-driven refresh below is the ground truth; this just prevents stale tokens.
DEFAULT_TOKEN_LIFETIME_SECONDS = 90 * 60
REFRESH_LEEWAY_SECONDS = 60


@dataclass
class SalesforceToken:
    access_token: str
    instance_url: str
    issued_at: float
    expires_at: float


@dataclass
class TokenStatus:
    configured: bool
    has_token: bool
    instance_url: str | None
    issued_at: float | None
    age_seconds: float | None
    last_error: str | None = None
    last_success_at: float | None = None


class SalesforceTokenCache:
    """Thread-safe single-token cache for the client-credentials flow."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: SalesforceToken | None = None
        self._last_error: str | None = None
        self._last_success_at: float | None = None

    def get(self) -> SalesforceToken:
        with self._lock:
            tok = self._token
            now = time.time()
            if tok is not None and (tok.expires_at - now) > REFRESH_LEEWAY_SECONDS:
                return tok
        return self._refresh()

    def force_refresh(self) -> SalesforceToken:
        return self._refresh()

    def status(self) -> TokenStatus:
        from app.config import get_settings

        s = get_settings()
        configured = bool(s.sf_client_id and s.sf_client_secret)
        with self._lock:
            tok = self._token
            if not tok:
                return TokenStatus(
                    configured=configured,
                    has_token=False,
                    instance_url=None,
                    issued_at=None,
                    age_seconds=None,
                    last_error=self._last_error,
                    last_success_at=self._last_success_at,
                )
            return TokenStatus(
                configured=configured,
                has_token=True,
                instance_url=tok.instance_url,
                issued_at=tok.issued_at,
                age_seconds=time.time() - tok.issued_at,
                last_error=self._last_error,
                last_success_at=self._last_success_at,
            )

    # ---- internals ----

    def _refresh(self) -> SalesforceToken:
        from app.config import get_settings

        s = get_settings()
        if not (s.sf_client_id and s.sf_client_secret):
            raise SalesforceAuthError("Salesforce credentials not configured")

        url = f"{s.sf_login_url.rstrip('/')}/services/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": s.sf_client_id,
            "client_secret": s.sf_client_secret,
        }
        try:
            resp = httpx.post(url, data=data, timeout=15.0)
        except httpx.HTTPError as exc:
            err = f"token request failed: {exc}"
            with self._lock:
                self._last_error = err
            raise SalesforceAuthError(err) from exc

        if resp.status_code != 200:
            err = f"token request status {resp.status_code}: {resp.text[:200]}"
            with self._lock:
                self._last_error = err
            raise SalesforceAuthError(err)

        body = resp.json()
        access = body.get("access_token")
        instance = body.get("instance_url")
        if not access or not instance:
            err = f"token response missing fields: {list(body.keys())}"
            with self._lock:
                self._last_error = err
            raise SalesforceAuthError(err)

        now = time.time()
        tok = SalesforceToken(
            access_token=access,
            instance_url=instance,
            issued_at=now,
            expires_at=now + DEFAULT_TOKEN_LIFETIME_SECONDS,
        )
        with self._lock:
            self._token = tok
            self._last_error = None
            self._last_success_at = now
        logger.info("Salesforce token refreshed (instance=%s)", instance)
        return tok


class SalesforceAuthError(Exception):
    """Raised when client-credentials auth cannot produce a token."""


class SalesforceSessionError(SalesforceAuthError):
    """Raised when a freshly minted token is still rejected by Salesforce.

    Distinct from SalesforceAuthError so callers can differentiate "we can't get
    a token at all" (credentials problem) from "Salesforce won't accept our
    token" (Connected App / integration user problem).
    """


@dataclass
class SfClient:
    """Thin wrapper around simple-salesforce that retries once on 401.

    Built lazily per call via the token cache so a stale instance never persists
    across a token rotation.
    """

    cache: SalesforceTokenCache
    _sf: Any = field(default=None, init=False, repr=False)
    _last_instance: str | None = field(default=None, init=False, repr=False)
    _last_session_id: str | None = field(default=None, init=False, repr=False)

    def _build(self) -> Any:
        from simple_salesforce import Salesforce  # imported lazily for tests

        tok = self.cache.get()
        # Rebuild on session_id rotation too: simple_salesforce caches the bearer
        # header in self.headers at __init__ time; reassigning session_id alone
        # leaves the old Authorization header in place and the 401 loops forever.
        if (
            self._sf is None
            or self._last_instance != tok.instance_url
            or self._last_session_id != tok.access_token
        ):
            self._sf = Salesforce(
                instance_url=tok.instance_url,
                session_id=tok.access_token,
            )
            self._last_instance = tok.instance_url
            self._last_session_id = tok.access_token
        return self._sf

    def query(self, soql: str) -> dict[str, Any]:
        from simple_salesforce.exceptions import SalesforceExpiredSession

        sf = self._build()
        try:
            return sf.query(soql)
        except SalesforceExpiredSession as exc:
            logger.info("Salesforce 401 — forcing token refresh and retrying once")
            self.cache.force_refresh()
            sf = self._build()
            try:
                return sf.query(soql)
            except SalesforceExpiredSession as exc2:
                raise SalesforceSessionError(str(exc2)) from exc2

    def query_all(self, soql: str) -> dict[str, Any]:
        from simple_salesforce.exceptions import SalesforceExpiredSession

        sf = self._build()
        try:
            return sf.query_all(soql)
        except SalesforceExpiredSession:
            self.cache.force_refresh()
            sf = self._build()
            try:
                return sf.query_all(soql)
            except SalesforceExpiredSession as exc2:
                raise SalesforceSessionError(str(exc2)) from exc2


# ---- module-level accessors (FastAPI dependency targets) ----

_cache: Optional[SalesforceTokenCache] = None
_cache_lock = threading.Lock()


def get_token_cache() -> SalesforceTokenCache:
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = SalesforceTokenCache()
    return _cache


def reset_token_cache() -> None:
    """Test helper — clears the cached token + cache singleton."""
    global _cache
    with _cache_lock:
        _cache = None


@lru_cache
def get_sf_client() -> SfClient:
    return SfClient(cache=get_token_cache())


def reset_sf_client_cache() -> None:
    get_sf_client.cache_clear()
