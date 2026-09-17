# Live / manual verification tier

Not run by CI (no `*_test.py` suffix, no `__init__.py`, not discovered by
`unittest discover`). This is what the offline suite (`tests/`) structurally
cannot prove, because it mocks Google at every boundary. Run these by hand:

- once before merging the MCP SDK v2 upgrade, against a locally built
  container with real `GOOGLE_ANALYTICS_MCP_OAUTH_*` credentials
- once again after the branch is deployed to the dev environment

## Checklist

1. **The real Google OAuth dance completes.** Offline tests mock
   `_extract_upstream_claims` and `verify_token`; nobody checks that Google
   actually accepts our `client_id`, redirect URI, consent parameters, or the
   `external` consent mode.

   ```bash
   docker build -t ga4-mcp-live .
   docker run --rm -p 8000:8000 --env-file local.env ga4-mcp-live
   ```

   Connect Claude Desktop's native HTTP connector to
   `http://127.0.0.1:8000/mcp`, complete the browser consent screen, then run
   `run_report` against a real GA4 property and confirm real rows come back.

2. **The issued token actually carries `analytics.readonly`, and the GA4
   Data API accepts it.** The offline suite only asserts the scope string is
   in a list; this is the one failure mode mocks can never surface.

3. **`httpx2` + `truststore` TLS on musl, on the live token exchange.**
   `fastmcp`'s `OAuthProxy` verifies via the OS trust store, not certifi.
   The CA bundle inside `python:3.14-alpine` was confirmed present, but the
   actual token exchange round trip through it was not — this is the run
   that proves it. A TLS failure here is a full outage that no unit test
   would ever see.

4. **`mode="2026-07-28"` negotiates correctly against an authenticated HTTP
   endpoint.** `mode="auto"` is known to fall back to the legacy era against
   an authenticated endpoint (fastmcp's own client sends the
   `server/discover` probe before attaching the OAuth token, gets a 401, and
   wrongly treats that as "not modern"). Pin the mode explicitly:

   ```python
   from fastmcp import Client

   async with Client(url, auth="oauth", mode="2026-07-28") as client:
       print(client.protocol_version)  # expect "2026-07-28"
   ```

5. **Session/transport behaviour under a real proxy, sessionless.**
   `stateless_http=True` behind GKE ingress with the 2026-07-28 revision:
   reconnects work, no sticky-session assumptions leak in.

6. **Persistent storage.** `GOOGLE_ANALYTICS_MCP_AUTH_STORAGE_TYPE=redis`
   with the Fernet wrapper — offline tests only ever exercise `in-memory`.
   Prove a token survives a pod restart.

7. **Claude Desktop's actual schema tolerance.** The
   `additionalProperties`-boolean invariant in `tests/schema_test.py` encodes
   a belief about a third-party client. Only Claude Desktop connecting and
   successfully calling every tool (including `run_funnel_report`, the one
   documented exception) confirms it.

8. **`/healthz` through the real ingress**, with probe timings, against the
   dev deployment post-rollout.

9. **Against dev, fingerprint the negotiated era from outside fastmcp's own
   client** — e.g. `claude mcp add --transport http ga4-dev <dev-url>` and
   `claude --debug mcp --debug-file <path>`, then grep the debug log for
   `"Connection established with capabilities"` and confirm
   `"negotiatedProtocolVersion":"2026-07-28"`. This is the technique that
   isolated the `mode="auto"` fallback as a fastmcp-client-only issue in the
   sibling `google-ads-mcp` upgrade — it is not a general MCP client
   limitation.
