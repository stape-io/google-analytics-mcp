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

"""Regenerates the wire goldens.

Run manually: `python -m tests.smoke.generate_golden`. Never run by CI --
review the diff in the PR that intentionally changes the wire output.
"""

import os

from tests.smoke import smoke_utils

HERE = os.path.dirname(__file__)


def main() -> None:
    for filename, fetch in (
        ("golden_tools_http.json", smoke_utils.get_http_tools_list),
        ("golden_tools_stdio.json", smoke_utils.get_stdio_tools_list),
    ):
        path = os.path.join(HERE, filename)
        with open(path, "w") as f:
            f.write(smoke_utils.normalize(fetch()))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
