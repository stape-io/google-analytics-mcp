from __future__ import annotations

import logging
from typing import Any, cast

import httpx
from fastmcp.server.auth.providers.google import (
    GoogleProvider as _SDKGoogleProvider,
)

logger = logging.getLogger(__name__)


async def get_google_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())


USER_PROFILE_SCOPES = {
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
}

USER_PROFILE_KEYS = {"email", "verified_email", "name", "picture"}


class GoogleProvider(_SDKGoogleProvider):
    async def _extract_upstream_claims(
        self, idp_tokens: dict[str, Any]
    ) -> dict[str, Any] | None:
        upstream_claims = await super()._extract_upstream_claims(idp_tokens)
        access_token = idp_tokens.get("access_token")
        if not access_token:
            return upstream_claims
        scope_str: str | None = idp_tokens.get("scope", "")
        if not scope_str:
            return upstream_claims
        scopes: list[str] = scope_str.split(" ")
        if not USER_PROFILE_SCOPES.intersection(scopes):
            return upstream_claims
        user_profile_data = await get_google_user_info(access_token)
        additional_claims = {
            k: v
            for k in USER_PROFILE_KEYS
            if (v := user_profile_data.get(k)) is not None
        }
        if additional_claims:
            upstream_claims = {**(upstream_claims or {}), **additional_claims}
        return upstream_claims
