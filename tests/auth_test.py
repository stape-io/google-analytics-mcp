# Copyright 2026 Stape
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Auth package coverage.

Production runs GOOGLE_ANALYTICS_MCP_AUTH_PROVIDER=google, so GoogleProvider /
OAuthProxy is the live path, and none of it was exercised anywhere before
this file. The upgrade risk is kwarg and hook drift, not logic:
get_google_auth_provider hands 8 keyword arguments straight to the SDK
provider, TokenVerifier calls a bare super().__init__() and then hand-sets
five attributes, and GoogleProvider overrides a PRIVATE SDK hook. Each is a
rename away from failing at boot -- i.e. after the image ships. So these
tests go *through* the factories, not around them.
"""

import os
import unittest
from unittest import mock

import httpx

BASE_URL = "https://ga-mcp.example.test"

# A syntactically valid Fernet key (32 url-safe base64-encoded bytes), inert
# and used only to construct the wrapper -- no ciphertext in this suite is
# ever decrypted with it. Set explicitly because in pydantic-settings,
# environment variables take precedence over the dotenv file -- belt and
# braces with the GOOGLE_ANALYTICS_MCP_ENV_FILE redirect in tests/__init__.py.
_FERNET_KEY = "oKmnyvtbXvrGAJbQbs6JUcs-ligaQj9bonNZgd5OLz4="
AUTH_ENV = {
    "GOOGLE_ANALYTICS_MCP_OAUTH_CLIENT_ID": "test.apps.googleusercontent.com",
    "GOOGLE_ANALYTICS_MCP_OAUTH_CLIENT_SECRET": "GOCSPX-test-secret",
    "GOOGLE_ANALYTICS_MCP_OAUTH_REQUIRE_AUTHORIZATION_CONSENT": "external",
    "GOOGLE_ANALYTICS_MCP_AUTH_STORAGE_TYPE": "in-memory",
    "GOOGLE_ANALYTICS_MCP_AUTH_STORAGE_ENCRYPTION_KEY": _FERNET_KEY,
}


class _AuthEnvTestCase(unittest.TestCase):
    def setUp(self) -> None:
        # setUp + addCleanup, not @mock.patch.dict as a decorator: decorator
        # dict-patching interacts badly with async test methods across
        # versions.
        patcher = mock.patch.dict(os.environ, AUTH_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)


class AuthProviderFactoryTest(_AuthEnvTestCase):
    def test_google_provider_builds(self) -> None:
        """Guards the 8 kwargs handed to the SDK GoogleProvider."""
        from analytics_mcp import auth
        from analytics_mcp.auth.google_provider import GoogleProvider
        from analytics_mcp.auth.settings import (
            GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
        )

        provider = auth.get_google_auth_provider(BASE_URL)

        self.assertIsInstance(provider, GoogleProvider)
        self.assertEqual(
            provider.required_scopes, GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES
        )

    def test_analytics_readonly_scope_is_requested(self) -> None:
        """Dropping this scope yields a token that fails on every GA4 call."""
        from analytics_mcp.auth.settings import (
            GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
        )

        self.assertIn(
            "https://www.googleapis.com/auth/analytics.readonly",
            GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
        )

    def test_remote_provider_builds(self) -> None:
        from analytics_mcp import auth
        from analytics_mcp.auth.settings import (
            GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
        )

        provider = auth.get_remote_auth_provider(
            BASE_URL, "https://accounts.google.com"
        )

        self.assertEqual(
            provider.token_verifier.required_scopes,
            GOOGLE_ANALYTICS_MCP_REQUIRED_SCOPES,
        )

    def test_remote_provider_requires_auth_server_url(self) -> None:
        from analytics_mcp import auth

        with self.assertRaises(ValueError):
            auth.get_remote_auth_provider(BASE_URL, None)

    def test_no_auth_provider_when_unset(self) -> None:
        """Stdio and local dev must boot with no auth env at all."""
        from analytics_mcp import auth

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(auth.get_auth_provider())


class TokenVerifierTest(_AuthEnvTestCase, unittest.IsolatedAsyncioTestCase):
    """TokenVerifier subclasses the SDK class, calls a bare super().__init__()
    and then assigns url/method/auth/required_scopes/content_type directly.
    If the SDK base ever becomes a pydantic model with required fields or
    frozen attributes, that pattern breaks at import- or first-request time.
    """

    def setUp(self) -> None:
        super().setUp()
        from analytics_mcp import auth

        self.verifier = auth.get_token_verifier()

    def test_defaults_from_settings(self) -> None:
        self.assertEqual(
            self.verifier.url,
            "https://www.googleapis.com/oauth2/v1/tokeninfo",
        )
        self.assertEqual(self.verifier.method, "GET")
        self.assertIsNone(self.verifier.auth)

    def test_request_kwargs_per_method(self) -> None:
        """GET puts the token in the query string; a form POST puts it in
        data. Getting this wrong sends the access token to the wrong
        place."""
        from analytics_mcp.auth.token_verifier import TokenVerifyRequest

        request = TokenVerifyRequest(access_token="tok")

        self.assertEqual(
            self.verifier._to_request_kwargs(request),
            {"params": {"access_token": "tok"}},
        )

        self.verifier.method = "POST"
        self.verifier.content_type = "application/x-www-form-urlencoded"
        self.assertEqual(
            self.verifier._to_request_kwargs(request),
            {"data": {"access_token": "tok"}},
        )

    async def test_verify_token_maps_tokeninfo_response(self) -> None:
        response = httpx.Response(
            200,
            json={
                "issued_to": "test.apps.googleusercontent.com",
                "audience": "test.apps.googleusercontent.com",
                "scope": (
                    "openid "
                    "https://www.googleapis.com/auth/analytics.readonly"
                ),
                "expires_in": 3599,
            },
            request=httpx.Request("GET", "https://tokeninfo.invalid"),
        )
        with mock.patch.object(
            httpx.AsyncClient,
            "request",
            new=mock.AsyncMock(return_value=response),
        ):
            token = await self.verifier.verify_token("tok")

        assert token is not None
        # AccessToken.client_id is populated from the tokeninfo response's
        # `audience` field, not `issued_to` -- verified against
        # token_verifier.py's verify_token, which builds
        # AccessToken(client_id=token_info.audience, ...).
        self.assertEqual(token.client_id, "test.apps.googleusercontent.com")
        self.assertIn(
            "https://www.googleapis.com/auth/analytics.readonly",
            token.scopes,
        )
        self.assertIsNotNone(token.expires_at)

    async def test_verify_token_returns_none_on_http_error(self) -> None:
        """A 401 from Google must be a rejected token, not a 500 from us."""
        response = httpx.Response(
            401, request=httpx.Request("GET", "https://tokeninfo.invalid")
        )
        with mock.patch.object(
            httpx.AsyncClient,
            "request",
            new=mock.AsyncMock(return_value=response),
        ):
            self.assertIsNone(await self.verifier.verify_token("bad"))


class ExtractUpstreamClaimsTest(
    _AuthEnvTestCase, unittest.IsolatedAsyncioTestCase
):
    """Covers the override of a PRIVATE SDK hook.

    mock.patch.object against the parent class doubles as the tripwire: if a
    future FastMCP renames or removes _extract_upstream_claims, patch.object
    raises AttributeError and this fails loudly -- instead of our subclass
    quietly becoming dead code whose email/name claims never reach a token
    again, which nothing else in the system would notice.
    """

    def setUp(self) -> None:
        super().setUp()
        from analytics_mcp import auth

        self.provider = auth.get_google_auth_provider(BASE_URL)

    def test_hook_exists_on_sdk_base(self) -> None:
        """Standalone tripwire, independent of the behavioural tests below."""
        from fastmcp.server.auth.providers.google import (
            GoogleProvider as SDK,
        )

        self.assertTrue(hasattr(SDK, "_extract_upstream_claims"))

    async def test_merges_user_profile_claims(self) -> None:
        from fastmcp.server.auth.providers.google import (
            GoogleProvider as SDK,
        )

        with (
            mock.patch.object(
                SDK,
                "_extract_upstream_claims",
                new=mock.AsyncMock(return_value={"sub": "123"}),
            ),
            mock.patch(
                "analytics_mcp.auth.google_provider.get_google_user_info",
                new=mock.AsyncMock(
                    return_value={
                        "email": "someone@example.test",
                        "name": "Some One",
                        # USER_PROFILE_KEYS is an explicit allowlist
                        # (email, verified_email, name, picture) -- this key
                        # must be dropped, not merged in.
                        "unexpected": "dropped",
                    }
                ),
            ),
        ):
            claims = await self.provider._extract_upstream_claims(
                {
                    "access_token": "tok",
                    "scope": "https://www.googleapis.com/auth/userinfo.email",
                }
            )

        self.assertEqual(
            claims,
            {
                "sub": "123",
                "email": "someone@example.test",
                "name": "Some One",
            },
        )

    async def test_no_profile_scope_skips_userinfo(self) -> None:
        """No profile scope -> no extra network call to Google."""
        from fastmcp.server.auth.providers.google import (
            GoogleProvider as SDK,
        )

        userinfo = mock.AsyncMock()
        with (
            mock.patch.object(
                SDK,
                "_extract_upstream_claims",
                new=mock.AsyncMock(return_value={"sub": "123"}),
            ),
            mock.patch(
                "analytics_mcp.auth.google_provider.get_google_user_info",
                new=userinfo,
            ),
        ):
            claims = await self.provider._extract_upstream_claims(
                {
                    "access_token": "tok",
                    "scope": "https://www.googleapis.com/auth/analytics.readonly",
                }
            )

        self.assertEqual(claims, {"sub": "123"})
        userinfo.assert_not_called()

    async def test_missing_access_token_falls_through(self) -> None:
        from fastmcp.server.auth.providers.google import (
            GoogleProvider as SDK,
        )

        with mock.patch.object(
            SDK,
            "_extract_upstream_claims",
            new=mock.AsyncMock(return_value={"sub": "123"}),
        ):
            claims = await self.provider._extract_upstream_claims({"scope": ""})

        self.assertEqual(claims, {"sub": "123"})


if __name__ == "__main__":
    unittest.main()
