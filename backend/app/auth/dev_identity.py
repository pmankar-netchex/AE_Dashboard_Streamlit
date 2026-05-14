from __future__ import annotations

from app.config import Settings
from app.schemas.common import CurrentUser


def build_dev_user(settings: Settings) -> CurrentUser:
    return CurrentUser(
        email=settings.dev_user_email.lower(),
        role=settings.dev_role,
        source="dev",
    )
