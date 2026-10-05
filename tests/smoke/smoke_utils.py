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

"""Raw JSON-RPC helpers for the stdio golden.

Deliberately does not use fastmcp.Client for the stdio side: this tier exists
to prove the bytes on the wire, so the only MCP implementation involved
should be the server's own.
"""

import contextlib
import json
import os
import re
import subprocess
import sys
import typing
from typing import Any

# Pinned, not mcp.types.LATEST_PROTOCOL_VERSION. This tier asserts the oldest
# handshake a real client (Claude Desktop, mcp-remote) might still open with,
# and must keep passing when the SDK's notion of "latest" moves.
LEGACY_PROTOCOL_VERSION = "2024-11-05"


def _hermetic_env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("GOOGLE_ANALYTICS_MCP_")
    }
    env["GOOGLE_ANALYTICS_MCP_ENV_FILE"] = os.path.join(
        os.path.dirname(__file__), "no-such.env"
    )
    return env


def start_server_process() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "analytics_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        env=_hermetic_env(),
        text=True,
        bufsize=0,
    )


def send_request(
    process: subprocess.Popen,
    method: str,
    params: dict | None = None,
    req_id: int | None = 1,
) -> None:
    request: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if req_id is not None:
        request["id"] = req_id
    if params:
        request["params"] = params
    assert process.stdin is not None
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()


def read_response(process: subprocess.Popen) -> dict[str, Any]:
    assert process.stdout is not None
    for line in process.stdout:
        try:
            return typing.cast(dict[str, Any], json.loads(line))
        except json.JSONDecodeError:
            continue  # the server may log non-JSON lines to stdout
    raise RuntimeError("Server closed connection without a response")


@contextlib.contextmanager
def initialized_server() -> typing.Iterator[subprocess.Popen]:
    process = start_server_process()
    try:
        send_request(
            process,
            "initialize",
            {
                "protocolVersion": LEGACY_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "1.0"},
            },
            req_id=1,
        )
        response = read_response(process)
        if "error" in response:
            raise RuntimeError(f"Initialize failed: {response['error']}")
        send_request(process, "notifications/initialized", req_id=None)
        yield process
    finally:
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()
        process.terminate()
        process.wait()


def get_stdio_tools_list() -> dict[str, Any]:
    """tools/list as it appears on the stdio wire."""
    with initialized_server() as process:
        send_request(process, "tools/list", req_id=2)
        response = read_response(process)
        if "error" in response:
            raise RuntimeError(f"tools/list failed: {response['error']}")
        return typing.cast(dict[str, Any], response["result"])


def get_http_tools_list() -> dict[str, Any]:
    """tools/list from the FastMCP object uvicorn serves, in process."""
    import asyncio

    from analytics_mcp.fastmcp_app import mcp
    from fastmcp import Client

    async def _list() -> list[dict[str, Any]]:
        async with Client(mcp) as client:
            return [
                t.model_dump(mode="json", exclude_none=True)
                for t in await client.list_tools()
            ]

    return {"tools": asyncio.run(_list())}


def normalize(payload: dict[str, Any]) -> str:
    payload["tools"].sort(key=lambda t: t.get("name", ""))
    for tool in payload["tools"]:
        # The reporting tools' descriptions embed `func.__doc__` in an
        # f-string. Python 3.13+ strips docstring indentation at compile
        # time and <=3.12 does not, so the raw text differs by interpreter
        # even with identical dependencies. Drop leading whitespace per line
        # so goldens compare equal on every supported Python.
        if "description" in tool:
            tool["description"] = re.sub(
                r"(?m)^[ \t]+", "", tool["description"]
            )
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
