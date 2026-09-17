# Copyright 2025 Google LLC All Rights Reserved.
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

"""Protocol-era and deployed-app coverage.

Nothing else in the suite speaks the protocol in-process: tests/smoke pins a
raw JSON-RPC handshake over stdio, and the schema/tool tests call functions
directly. These are the only assertions that the modern, sessionless MCP
revision (2026-07-28) is served at all, alongside the legacy 2025-11-25 era.
"""

import unittest

from fastmcp import Client

# fastmcp's Client gained era negotiation (the `mode` kwarg and the
# `protocol_version` attribute) only in the v4 line, which ships with mcp 2.x.
# On the pre-upgrade stack (fastmcp 3.x) this is False, so
# ProtocolNegotiationTest self-arms the moment the SDK bump lands, with no
# red CI in the meantime.
_SUPPORTS_ERA_NEGOTIATION = hasattr(Client, "protocol_version")


@unittest.skipUnless(
    _SUPPORTS_ERA_NEGOTIATION,
    "fastmcp client era negotiation not available on this stack yet "
    "(requires the mcp 2.x / fastmcp 4.x upgrade)",
)
class ProtocolNegotiationTest(unittest.IsolatedAsyncioTestCase):
    async def _negotiate(self, mode: str) -> tuple[str, set[str]]:
        from analytics_mcp.fastmcp_app import mcp

        async with Client(mcp, mode=mode) as client:
            # Deliberately client.protocol_version, never
            # client.initialize_result: the modern era sends server/discover
            # instead of an initialize handshake, so that attribute is None.
            version = client.protocol_version
            tools = {t.name for t in await client.list_tools()}
        return version, tools

    async def test_negotiates_modern_protocol(self) -> None:
        """A 2026-era client must get 2026-07-28, not a silent 2025 fallback."""
        version, tools = await self._negotiate("auto")
        # Literal, not mcp.types.LATEST_PROTOCOL_VERSION: asserting the
        # constant against itself is tautological and would pass on any
        # future bump.
        self.assertEqual(version, "2026-07-28")
        self.assertIn("run_report", tools)

    async def test_legacy_clients_still_served(self) -> None:
        """Older clients keep working, with an identical tool inventory."""
        legacy_version, legacy_tools = await self._negotiate("legacy")
        _, modern_tools = await self._negotiate("auto")
        self.assertEqual(legacy_version, "2025-11-25")
        self.assertEqual(legacy_tools, modern_tools)
        self.assertEqual(len(legacy_tools), 9)


class HttpAppTest(unittest.TestCase):
    """The only coverage of the object uvicorn actually serves.

    chart/templates/deployment.yaml probes /healthz on both liveness and
    readiness. Losing this route fails every pod, not just MCP traffic.
    """

    def test_deployed_app_builds(self) -> None:
        import server

        self.assertIsNotNone(server.app)

    def test_healthz_route_is_registered(self) -> None:
        import server

        paths = [getattr(r, "path", None) for r in server.app.routes]
        self.assertIn("/healthz", paths)

    def test_healthz_returns_ok_without_auth(self) -> None:
        """The probe must answer 200 with no bearer token: kubelet sends
        none. A future auth middleware wrapping the whole app would break
        it."""
        from starlette.testclient import TestClient

        import server

        with TestClient(server.app) as client:
            response = client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
