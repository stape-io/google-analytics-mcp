import base64
import datetime as dt
import os
from typing import Any, Literal

from pydantic import (
    AnyHttpUrl,
    Field,
    RedisDsn,
    SecretBytes,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/analytics.readonly",
]

GOOGLE_ANALYTICS_MCP_PREFIX = "google_analytics_mcp"

GOOGLE_ANALYTICS_MCP_ENV_FILE = os.environ.get(
    f"{GOOGLE_ANALYTICS_MCP_PREFIX.upper()}_ENV_FILE", ".env"
)


def create_settings_config(path: tuple[str, ...]) -> SettingsConfigDict:
    if path:
        env_path = "_".join(part.lower() for part in path)
        env_path = f"{GOOGLE_ANALYTICS_MCP_PREFIX}_{env_path}"
    else:
        env_path = GOOGLE_ANALYTICS_MCP_PREFIX
    return SettingsConfigDict(
        env_prefix=env_path + "_",
        env_file=GOOGLE_ANALYTICS_MCP_ENV_FILE,
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class GoogleAnalyticsMCPJwtProviderSettings(BaseSettings):
    model_config = create_settings_config(("auth", "jwt", "provider"))

    private_keys: list[dict[str, Any]]
    algorithm: str | None = None
    token_lifetime: dt.timedelta = dt.timedelta(minutes=1)
    claims: dict[str, Any] = Field(default_factory=dict)


class GoogleAnalyticsMCPAuthStorageSettings(BaseSettings):
    model_config = create_settings_config(("auth", "storage"))

    type: Literal["in-memory", "redis", "disk"] | None = None
    redis_url: RedisDsn | None = None
    encryption_key: SecretBytes | None = None
    disk_directory: str | None = None

    @model_validator(mode="after")
    def validate_modeled_fields(
        self,
    ) -> "GoogleAnalyticsMCPAuthStorageSettings":
        if self.type == "redis" and not self.redis_url:
            raise ValueError("redis_url must be set when type is 'redis'")
        return self


class GoogleAnalyticsMCPTokenVerifierSettings(BaseSettings):
    model_config = create_settings_config(("auth", "token", "verifier"))

    url: str = "https://www.googleapis.com/oauth2/v1/tokeninfo"
    auth: Literal["bearer", "basic"] | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"] = "GET"
    content_type: Literal[
        "application/json", "application/x-www-form-urlencoded"
    ] = "application/json"

    bearer_token: SecretStr | None = None

    basic_auth_username: str | None = None
    basic_auth_password: SecretStr | None = None


class GoogleAnalyticsMCPOAuthSettings(BaseSettings):
    model_config = create_settings_config(("oauth",))

    client_id: str
    client_secret: SecretStr
    extra_authorize_params: dict[str, Any] | None = None
    require_authorization_consent: bool | Literal["external"] = "external"
    jwt_signing_key: SecretBytes | None = None

    @field_validator("jwt_signing_key", mode="before")
    @classmethod
    def get_jwt_signing_key(cls, v: Any) -> SecretBytes | None:
        if v is None:
            return None
        if isinstance(v, SecretStr):
            v = v.get_secret_value()
        if isinstance(v, str):
            v = base64.urlsafe_b64decode(v)
        if isinstance(v, bytes):
            return SecretBytes(v)
        if isinstance(v, SecretBytes):
            return v
        return None


class GoogleAnalyticsMCPSettings(BaseSettings):
    model_config = create_settings_config(())
    base_url: str = "http://127.0.0.1:8080"
    auth_provider: Literal["google", "remote"] | None = None
    auth_server_url: AnyHttpUrl | None = None
