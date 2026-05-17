import logging
from pathlib import Path

import httpx
from fastmcp.server.auth import AuthProvider, RemoteAuthProvider
from key_value.aio.protocols import AsyncKeyValue
from pydantic import AnyHttpUrl

from .google_provider import GoogleProvider
from .jwt import JWTProvider
from .settings import (
    GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
    GoogleAnalyticsMCPAuthStorageSettings,
    GoogleAnalyticsMCPJwtProviderSettings,
    GoogleAnalyticsMCPOAuthSettings,
    GoogleAnalyticsMCPSettings,
    GoogleAnalyticsMCPTokenVerifierSettings,
)
from .token_verifier import BearerAuth, TokenVerifier

logger = logging.getLogger(__name__)


def _get_jwt_provider() -> JWTProvider:
    from joserfc import jwk

    settings = GoogleAnalyticsMCPJwtProviderSettings()  # type: ignore[call-arg]
    if not settings.private_keys or settings.algorithm is None:
        raise ValueError(
            "JWTProvider cannot be created without private keys and algorithm."
        )

    private_keys = jwk.KeySet.import_key_set({"keys": settings.private_keys})

    return JWTProvider(
        private_keys=private_keys,
        algorithm=settings.algorithm,
        claims=settings.claims,
        token_lifetime=settings.token_lifetime,
    )


def _get_bearer_auth() -> httpx.Auth:
    settings = GoogleAnalyticsMCPTokenVerifierSettings()
    if settings.bearer_token is not None:
        bearer_token = settings.bearer_token.get_secret_value()
        return BearerAuth(token_provider=lambda: bearer_token)
    else:
        return BearerAuth(token_provider=_get_jwt_provider())


def _get_basic_auth() -> httpx.Auth:
    settings = GoogleAnalyticsMCPTokenVerifierSettings()
    if settings.basic_auth_username is None or settings.basic_auth_password is None:
        raise ValueError("Basic auth credentials are not configured.")
    return httpx.BasicAuth(
        username=settings.basic_auth_username,
        password=settings.basic_auth_password.get_secret_value(),
    )


def _get_token_verifier_auth(
) -> httpx.Auth | None:
    settings = GoogleAnalyticsMCPTokenVerifierSettings()
    if settings.auth is None:
        return None
    elif settings.auth == "bearer":
        return _get_bearer_auth()
    elif settings.auth == "basic":
        return _get_basic_auth()
    else:
        raise ValueError(f"Unsupported auth type: {settings.auth}")


def _get_auth_provider_storage() -> AsyncKeyValue | None:
    settings = GoogleAnalyticsMCPAuthStorageSettings()
    base_store: AsyncKeyValue | None = None
    if settings.type == "in-memory":
        from key_value.aio.stores.memory import MemoryStore

        base_store = MemoryStore()
    elif settings.type == "redis":
        if not settings.redis_url:
            raise ValueError("Redis URL must be provided for Redis storage.")
        from key_value.aio.stores.redis import RedisStore

        base_store = RedisStore(url=str(settings.redis_url))
    elif settings.type == "disk":
        from key_value.aio.stores.disk import DiskStore

        directory = settings.disk_directory or Path.cwd()
        base_store = DiskStore(directory=directory, auto_create=True)
    else:
        return None

    if not settings.encryption_key:
        logger.warning(
            "Auth storage is configured without encryption. This is not recommended for production use."
        )
        return base_store

    from cryptography.fernet import Fernet
    from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

    return FernetEncryptionWrapper(
        key_value=base_store,
        fernet=Fernet(settings.encryption_key.get_secret_value()),
    )


def get_token_verifier(
    required_scopes: list[str] | None = None,
) -> TokenVerifier:
    if required_scopes is None:
        required_scopes = GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES
    settings = GoogleAnalyticsMCPTokenVerifierSettings()
    return TokenVerifier(
        auth=_get_token_verifier_auth(),
        url=settings.url,
        method=settings.method,
        required_scopes=required_scopes,
        content_type=settings.content_type,
    )


def get_google_auth_provider(base_url: str) -> GoogleProvider:
    oauth_settings = GoogleAnalyticsMCPOAuthSettings()  # type: ignore[call-arg]
    if not oauth_settings.client_id or not oauth_settings.client_secret:
        raise ValueError(
            "GoogleProvider cannot be created without client ID and client secret."
        )
    client_storage = _get_auth_provider_storage()
    if client_storage is None:
        logger.warning(
            "No storage configured for GoogleProvider."
        )
    jwt_signing_key = None
    if not oauth_settings.jwt_signing_key:
        logger.warning(
            "No JWT signing key configured for GoogleProvider. JWT-based flows will not work."
        )
    else:
        jwt_signing_key = oauth_settings.jwt_signing_key.get_secret_value()
    return GoogleProvider(
        client_id=oauth_settings.client_id,
        client_secret=oauth_settings.client_secret.get_secret_value(),
        base_url=base_url,
        required_scopes=GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
        client_storage=client_storage,
        require_authorization_consent=oauth_settings.require_authorization_consent,
        extra_authorize_params=oauth_settings.extra_authorize_params,
        jwt_signing_key=jwt_signing_key,
    )


def get_remote_auth_provider(
    base_url: str, auth_server_url: AnyHttpUrl | str | None = None
) -> RemoteAuthProvider:
    if not auth_server_url:
        raise ValueError("Remote auth provider requires an auth server URL.")
    return RemoteAuthProvider(
        token_verifier=get_token_verifier(),
        authorization_servers=[AnyHttpUrl(auth_server_url)],
        base_url=base_url,
        scopes_supported=GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
    )


def get_auth_provider() -> AuthProvider | None:
    settings = GoogleAnalyticsMCPSettings()
    if settings.auth_provider is None:
        return None
    if settings.auth_provider == "google":
        return get_google_auth_provider(settings.base_url)
    elif settings.auth_provider == "remote":
        return get_remote_auth_provider(
            settings.base_url, settings.auth_server_url
        )
