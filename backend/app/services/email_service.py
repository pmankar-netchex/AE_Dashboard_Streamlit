from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Thin wrapper around the SendGrid HTTP API.

    `send_html()` is the single send path used by both scheduled jobs and the
    Send-Now endpoint. Returns the SendGrid message id (or '' if delivery was
    skipped because no API key is configured — useful in dev).
    """

    def send_html(
        self,
        *,
        to: list[str],
        subject: str,
        html: str,
        text: str | None = None,
    ) -> str:
        s = get_settings()
        if not s.sendgrid_api_key:
            logger.warning(
                "SENDGRID_API_KEY not set — would have sent to %s subject=%s",
                to,
                subject,
            )
            return ""

        # Lazy import so unit tests don't pay the cost
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
        except ImportError as exc:
            raise RuntimeError("sendgrid package not installed") from exc

        message = Mail(
            from_email=(s.sendgrid_from_email, s.sendgrid_from_name),
            to_emails=to,
            subject=subject,
            html_content=html,
            plain_text_content=text,
        )
        client = SendGridAPIClient(s.sendgrid_api_key)
        response = client.send(message)
        msg_id = response.headers.get("X-Message-Id", "") if hasattr(response, "headers") else ""
        logger.info(
            "email sent to %d recipient(s) (msg_id=%s status=%s)",
            len(to),
            msg_id,
            getattr(response, "status_code", "?"),
        )
        return msg_id


@lru_cache
def get_email_service() -> EmailService:
    return EmailService()


def reset_email_service() -> None:
    get_email_service.cache_clear()
