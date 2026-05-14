from __future__ import annotations

import logging
import time
from threading import Lock

from app.legacy import data_engine

logger = logging.getLogger(__name__)

_TTL_SECONDS = 300  # 5-min cache for filter lists


class FilterService:
    """TTL-cached wrapper around data_engine list helpers.

    Filter options change rarely (active AE roster, manager set) so we trade a
    little staleness for fewer SF round-trips.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._managers: tuple[float, list[str]] | None = None
        self._aes: dict[str | None, tuple[float, list[dict]]] = {}

    def managers(self, sf) -> list[str]:
        now = time.time()
        with self._lock:
            if self._managers and (now - self._managers[0]) < _TTL_SECONDS:
                return self._managers[1]
        names = data_engine.get_managers_list(sf)
        with self._lock:
            self._managers = (now, names)
        return names

    def aes(self, sf, manager: str | None = None) -> list[dict]:
        key = manager or None
        now = time.time()
        with self._lock:
            cached = self._aes.get(key)
            if cached and (now - cached[0]) < _TTL_SECONDS:
                return cached[1]
        rows = data_engine.get_ae_names_list(sf, manager_name=manager)
        with self._lock:
            self._aes[key] = (now, rows)
        return rows

    def invalidate(self) -> None:
        with self._lock:
            self._managers = None
            self._aes.clear()


_service: FilterService | None = None
_service_lock = Lock()


def get_filter_service() -> FilterService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = FilterService()
    return _service


def reset_filter_service() -> None:
    global _service
    with _service_lock:
        _service = None
