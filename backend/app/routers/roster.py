from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user, require_admin
from app.schemas.common import CurrentUser
from app.schemas.roster import RosterEntryOut, RosterImportResult, SfUserResult
from app.services.audit_service import get_audit_service
from app.services.filter_service import get_filter_service
from app.services.roster_service import get_roster_service
from app.services.salesforce_client import get_sf_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roster", tags=["roster"])

_NULL_ID_SENTINEL = "000000000000000"

_DEFAULT_IMPORT_WHERE = (
    "User_Role_Formula__c LIKE '%Sales Rep%'"
    " AND (NOT User_Role_Formula__c LIKE '%SDR%')"
    " AND (NOT User_Role_Formula__c LIKE '%Account%')"
)


def _fetch_sf_users(sf, *, where_extra: str = "", limit: int = 20) -> list[dict]:
    """Query SF User records with Manager + SDR relationship fields."""
    where_clause = f"AND {where_extra}" if where_extra else ""
    try:
        result = sf.query(f"""
            SELECT Id, Name, Email,
                   Manager.Name, Manager.Id,
                   Assigned_SDR_Outbound__c,
                   Assigned_SDR_Outbound__r.Name,
                   Assigned_SDR_Outbound__r.Email
            FROM User
            WHERE IsActive = true AND UserType = 'Standard' {where_clause}
            LIMIT {limit}
        """)
        out = []
        for r in result.get("records", []):
            mgr = r.get("Manager") or {}
            sdr_r = r.get("Assigned_SDR_Outbound__r") or {}
            out.append({
                "sf_id": r["Id"],
                "name": r.get("Name") or "",
                "email": r.get("Email") or "",
                "manager_name": mgr.get("Name") or "",
                "manager_id": mgr.get("Id") or "",
                "sdr_id": r.get("Assigned_SDR_Outbound__c") or "",
                "sdr_name": sdr_r.get("Name") or "",
                "sdr_email": sdr_r.get("Email") or "",
            })
        return out
    except Exception as exc:
        logger.warning("_fetch_sf_users failed: %s", exc)
        # Retry without SDR relationship traversal (field may not exist)
        try:
            result = sf.query(f"""
                SELECT Id, Name, Email, Manager.Name, Manager.Id,
                       Assigned_SDR_Outbound__c
                FROM User
                WHERE IsActive = true AND UserType = 'Standard' {where_clause}
                LIMIT {limit}
            """)
            out = []
            for r in result.get("records", []):
                mgr = r.get("Manager") or {}
                out.append({
                    "sf_id": r["Id"],
                    "name": r.get("Name") or "",
                    "email": r.get("Email") or "",
                    "manager_name": mgr.get("Name") or "",
                    "manager_id": mgr.get("Id") or "",
                    "sdr_id": r.get("Assigned_SDR_Outbound__c") or "",
                    "sdr_name": "",
                    "sdr_email": "",
                })
            return out
        except Exception as exc2:
            logger.exception("_fetch_sf_users fallback also failed: %s", exc2)
            return []


@router.get("", response_model=list[RosterEntryOut])
def list_roster(_: CurrentUser = Depends(get_current_user)) -> list[RosterEntryOut]:
    return get_roster_service().list()


@router.get("/search", response_model=list[SfUserResult])
def search_sf_users(
    q: str | None = Query(default=None),
    _: CurrentUser = Depends(require_admin),
) -> list[SfUserResult]:
    """List active SF users. With q (>=2 chars), filters by name/email server-side;
    otherwise returns up to 200 active users for client-side filtering."""
    sf = get_sf_client()
    if q and len(q) >= 2:
        q_safe = q.replace("'", "\\'")
        users = _fetch_sf_users(
            sf,
            where_extra=f"(Name LIKE '%{q_safe}%' OR Email LIKE '%{q_safe}%')",
            limit=50,
        )
    else:
        users = _fetch_sf_users(sf, limit=200)
    return [SfUserResult(**u) for u in users]


@router.post("/import", response_model=RosterImportResult)
def import_from_sf(user: CurrentUser = Depends(require_admin)) -> RosterImportResult:
    """Bulk-import AEs using the default Salesforce role filter."""
    sf = get_sf_client()
    users = _fetch_sf_users(sf, where_extra=_DEFAULT_IMPORT_WHERE, limit=200)
    if not users:
        # Default role filter matched nothing — import all active users so the
        # admin can see what's in SF and manually curate the list.
        logger.warning("import_from_sf: default role filter returned 0 — falling back to all active users")
        users = _fetch_sf_users(sf, limit=200)
    n = get_roster_service().bulk_import(users, actor=user.email)
    get_filter_service().invalidate()
    get_audit_service().write(
        actor=user.email,
        entity="roster",
        action="import",
        details={"count": n},
    )
    return RosterImportResult(imported=n)


@router.post("/{sf_id}", response_model=RosterEntryOut, status_code=201)
def add_to_roster(
    sf_id: str,
    user: CurrentUser = Depends(require_admin),
) -> RosterEntryOut:
    sf = get_sf_client()
    users = _fetch_sf_users(sf, where_extra=f"Id = '{sf_id}'", limit=1)
    if not users:
        raise HTTPException(404, detail="User not found in Salesforce")
    entry = get_roster_service().add(**users[0], actor=user.email)
    get_filter_service().invalidate()
    get_audit_service().write(
        actor=user.email,
        entity="roster",
        action="add",
        target=sf_id,
        details={"name": entry.name},
    )
    return entry


@router.delete("/{sf_id}", status_code=204)
def remove_from_roster(
    sf_id: str,
    user: CurrentUser = Depends(require_admin),
) -> None:
    if not get_roster_service().remove(sf_id):
        raise HTTPException(404, detail="Entry not found in roster")
    get_filter_service().invalidate()
    get_audit_service().write(
        actor=user.email,
        entity="roster",
        action="remove",
        target=sf_id,
    )
