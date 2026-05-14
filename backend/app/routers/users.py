from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user, require_admin
from app.schemas.common import CurrentUser
from app.schemas.users import UserCreateIn, UserOut, UserUpdateIn
from app.services.audit_service import get_audit_service
from app.services.user_service import UserRow, get_user_service

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_out(row: UserRow) -> UserOut:
    return UserOut(
        email=row.email,
        role=row.role,
        is_active=row.is_active,
        added_by=row.added_by,
        added_at=row.added_at,
    )


@router.get("", response_model=list[UserOut])
def list_users(_: CurrentUser = Depends(get_current_user)) -> list[UserOut]:
    return [_to_out(u) for u in get_user_service().list()]


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreateIn, actor: CurrentUser = Depends(require_admin)
) -> UserOut:
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(400, detail="email required")
    svc = get_user_service()
    if svc.get(email) is not None:
        raise HTTPException(409, detail="user already exists")
    row = svc.upsert(
        UserRow(email=email, role=body.role, is_active=body.is_active),
        actor=actor.email,
    )
    get_audit_service().write(
        actor=actor.email,
        entity="user",
        action="create",
        target=email,
        details={"role": row.role, "is_active": row.is_active},
    )
    return _to_out(row)


@router.put("/{email}", response_model=UserOut)
def update_user(
    email: str, body: UserUpdateIn, actor: CurrentUser = Depends(require_admin)
) -> UserOut:
    svc = get_user_service()
    existing = svc.get(email)
    if existing is None:
        raise HTTPException(404, detail="user not found")
    row = svc.upsert(
        UserRow(
            email=existing.email,
            role=body.role if body.role is not None else existing.role,
            is_active=body.is_active if body.is_active is not None else existing.is_active,
            added_by=existing.added_by,
            added_at=existing.added_at,
        ),
        actor=actor.email,
    )
    get_audit_service().write(
        actor=actor.email,
        entity="user",
        action="update",
        target=existing.email,
        details={"role": row.role, "is_active": row.is_active},
    )
    return _to_out(row)


@router.delete("/{email}", status_code=204)
def delete_user(
    email: str, actor: CurrentUser = Depends(require_admin)
) -> None:
    if email.strip().lower() == actor.email.lower():
        raise HTTPException(400, detail="cannot delete yourself")
    svc = get_user_service()
    if not svc.delete(email, actor=actor.email):
        raise HTTPException(404, detail="user not found")
    get_audit_service().write(
        actor=actor.email,
        entity="user",
        action="delete",
        target=email.strip().lower(),
    )
    return None
