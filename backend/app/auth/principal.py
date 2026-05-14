from __future__ import annotations

import base64
import binascii
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_x_ms_client_principal(header_value: str | None) -> dict[str, Any] | None:
    """Decode the base64 JSON Easy Auth principal header.

    Returns a dict with keys: email, oid, name, idp, claims. Returns None if the
    header is missing or malformed.
    """
    if not header_value:
        return None
    try:
        raw = base64.b64decode(header_value)
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError):
        logger.warning("invalid X-MS-CLIENT-PRINCIPAL: cannot decode")
        return None

    claims_list = payload.get("claims") or []
    by_type: dict[str, str] = {}
    for c in claims_list:
        t = c.get("typ") or c.get("type")
        v = c.get("val") or c.get("value")
        if t and v and t not in by_type:
            by_type[t] = v

    email = (
        by_type.get("emails")
        or by_type.get("email")
        or by_type.get("preferred_username")
        or by_type.get("upn")
        or by_type.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
        or payload.get("userPrincipalName")
        or payload.get("userId")
    )
    oid = (
        by_type.get("oid")
        or by_type.get("http://schemas.microsoft.com/identity/claims/objectidentifier")
    )
    name = by_type.get("name") or by_type.get("given_name")
    idp = payload.get("identityProvider") or by_type.get("idp")

    if not email:
        return None

    return {
        "email": str(email).lower(),
        "oid": oid,
        "name": name,
        "idp": idp,
        "claims": by_type,
    }
