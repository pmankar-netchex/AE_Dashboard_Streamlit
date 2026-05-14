from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "prod"] = Field(default="dev", validation_alias="ENV")

    # Dev-only identity (ignored when env=prod)
    dev_role: Literal["admin", "user"] = Field(default="admin", validation_alias="DEV_ROLE")
    dev_user_email: str = Field(default="dev@local", validation_alias="DEV_USER_EMAIL")

    # Bootstrap admins (comma-separated) seeded into users table on startup
    bootstrap_admin_emails: str = Field(default="", validation_alias="BOOTSTRAP_ADMIN_EMAILS")

    # Salesforce (client-credentials)
    sf_client_id: str = Field(default="", validation_alias="SF_CLIENT_ID")
    sf_client_secret: str = Field(default="", validation_alias="SF_CLIENT_SECRET")
    sf_login_url: str = Field(
        default="https://login.salesforce.com", validation_alias="SF_LOGIN_URL"
    )
    sf_api_version: str = Field(default="v60.0", validation_alias="SF_API_VERSION")

    # Azure Table Storage
    azure_storage_connection_string: str = Field(
        default="", validation_alias="AZURE_STORAGE_CONNECTION_STRING"
    )

    # Query write-gate
    allow_prod_query_writes: bool = Field(
        default=False, validation_alias="ALLOW_PROD_QUERY_WRITES"
    )

    # Email
    sendgrid_api_key: str = Field(default="", validation_alias="SENDGRID_API_KEY")
    sendgrid_from_email: str = Field(
        default="dashboard@example.com", validation_alias="SENDGRID_FROM_EMAIL"
    )
    sendgrid_from_name: str = Field(
        default="AE Dashboard", validation_alias="SENDGRID_FROM_NAME"
    )

    # Scheduler
    scheduler_tz: str = Field(default="America/Chicago", validation_alias="SCHEDULER_TZ")

    # CORS / internal
    ui_origin: str = Field(default="http://localhost:5173", validation_alias="UI_ORIGIN")
    internal_api_key: str = Field(default="", validation_alias="INTERNAL_API_KEY")

    @property
    def bootstrap_admin_list(self) -> list[str]:
        raw = self.bootstrap_admin_emails or ""
        return [e.strip().lower() for e in raw.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
