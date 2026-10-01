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

"""Golden-wire tests.

There are two schema producers today (the ADK/low-level stdio stack and the
FastMCP/HTTP stack) and one after the MCP SDK v2 upgrade unifies them. Each
golden gets a different contract:

- golden_tools_http.json is the production path. It must not change across
  the upgrade beyond the one documented delta (each tool gains a `title`).
  This is the literal "no regression" promise.
- golden_tools_stdio.json captures the pre-upgrade ADK era. The upgrade PR
  regenerates it once, and that diff *is* the review.

Not golden'd: resources/list. This server has no MCP resources, so a golden
here could only ever fail when someone adds a legitimate feature.
"""

import difflib
import os
import unittest

from tests.smoke import smoke_utils

HERE = os.path.dirname(__file__)


class GoldenTest(unittest.TestCase):
    def _assert_matches(self, filename: str, payload: dict) -> None:
        path = os.path.join(HERE, filename)
        current = smoke_utils.normalize(payload)
        if not os.path.exists(path):
            self.fail(
                f"{path} missing. Run: python -m tests.smoke.generate_golden"
            )
        with open(path) as f:
            golden = f.read()
        if current != golden:
            diff = "\n".join(
                difflib.unified_diff(
                    golden.splitlines(),
                    current.splitlines(),
                    fromfile=filename,
                    tofile="current",
                    lineterm="",
                )
            )
            self.fail(
                f"{filename} drifted. If this is an intended change, "
                f"regenerate with `python -m tests.smoke.generate_golden` "
                f"and review the diff in the PR:\n{diff}"
            )

    def test_http_tools_list_matches_golden(self) -> None:
        """The production path. Must survive the upgrade unchanged (beyond
        the documented +title delta)."""
        self._assert_matches(
            "golden_tools_http.json", smoke_utils.get_http_tools_list()
        )

    def test_stdio_tools_list_matches_golden(self) -> None:
        """The stdio path. Expected to change exactly once, in the upgrade
        PR that regenerates this file."""
        self._assert_matches(
            "golden_tools_stdio.json", smoke_utils.get_stdio_tools_list()
        )


if __name__ == "__main__":
    unittest.main()
