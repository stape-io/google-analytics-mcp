#!/usr/bin/env python

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

"""Entry point for the Google Analytics MCP server over stdio."""

from analytics_mcp.fastmcp_app import mcp


def run_server() -> None:
    """Runs the MCP server over standard I/O."""
    # show_banner=False: the banner calls PyPI for an update check on every
    # client launch.
    mcp.run(show_banner=False)


if __name__ == "__main__":
    run_server()
