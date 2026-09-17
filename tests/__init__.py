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

"""Test package init.

Runs before any analytics_mcp import, because unittest discovery imports this
package first. Two jobs:

1. Point pydantic-settings at a path that cannot exist, so a developer's
   gitignored .env can never change a test outcome.
   GOOGLE_ANALYTICS_MCP_ENV_FILE is read at *import* of
   analytics_mcp.auth.settings (module-level, not per-instantiation), so
   patching it from setUp() would be too late.
2. Drop any GOOGLE_ANALYTICS_MCP_* already in the shell, so an exported
   GOOGLE_ANALYTICS_MCP_AUTH_PROVIDER=google doesn't make
   `import analytics_mcp.fastmcp_app` try to build a real OAuth provider.
"""

import os

os.environ["GOOGLE_ANALYTICS_MCP_ENV_FILE"] = os.path.join(
    os.path.dirname(__file__), "no-such.env"
)
for _key in [k for k in os.environ if k.startswith("GOOGLE_ANALYTICS_MCP_")]:
    if _key != "GOOGLE_ANALYTICS_MCP_ENV_FILE":
        del os.environ[_key]
