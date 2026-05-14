from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.storage.tables import ALL_TABLES, TABLE_USERS, get_service, get_table_client

logger = logging.getLogger(__name__)


def ensure_tables() -> list[str]:
    """Create every table this app needs if it doesn't already exist.

    Returns the list of tables that were created (may be empty). No-op when
    Azure Table Storage isn't configured (dev with no connection string).
    """
    svc = get_service()
    if svc is None:
        logger.info("storage not configured; skipping ensure_tables")
        return []
    created: list[str] = []
    for name in ALL_TABLES:
        try:
            svc.create_table(name)
            created.append(name)
            logger.info("created table %s", name)
        except Exception as exc:  # azure ResourceExistsError or transient
            if "TableAlreadyExists" in str(exc) or "already exists" in str(exc).lower():
                continue
            logger.warning("ensure_tables: %s -> %s", name, exc)
    return created


def bootstrap_admins(emails: list[str]) -> int:
    """Upsert each email as role=admin, is_active=True. Idempotent.

    Returns the number of admins upserted. No-op when storage isn't configured.
    """
    if not emails:
        return 0
    client = get_table_client(TABLE_USERS)
    if client is None:
        return 0
    n = 0
    now = datetime.now(timezone.utc).isoformat()
    for raw in emails:
        email = raw.strip().lower()
        if not email:
            continue
        try:
            client.upsert_entity(
                {
                    "PartitionKey": "user",
                    "RowKey": email,
                    "Email": email,
                    "Role": "admin",
                    "IsActive": True,
                    "AddedBy": "bootstrap",
                    "AddedAt": now,
                }
            )
            n += 1
        except Exception:
            logger.exception("bootstrap_admins: upsert failed for %s", email)
    if n:
        logger.info("bootstrapped %d admin(s)", n)
    return n
