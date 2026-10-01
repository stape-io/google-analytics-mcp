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

"""Schema invariants that must hold no matter which stack generates them.

Each invariant here is the assertion form of one hand-written fixup in
analytics_mcp/coordinator.py, which the MCP SDK v2 upgrade deletes (the stdio
path is unified onto the same FastMCP server that already serves production
HTTP). Measured against the pre-upgrade code, three of those four fixups are
already no-ops -- but that was only ever true by accident, and nothing
recorded it. Now something does.
"""

import asyncio
import importlib.util
import typing
import unittest

TOOL_NAMES = {
    "get_account_summaries",
    "get_custom_dimensions_and_metrics",
    "get_property_details",
    "list_google_ads_links",
    "list_property_annotations",
    "run_conversions_report",
    "run_funnel_report",
    "run_realtime_report",
    "run_report",
}

# The coordinator injected these by hand. FastMCP derives the same lists from
# the function signatures; this pins them so a "convenience" default on any
# of the four core params silently turning a required arg optional is caught.
REQUIRED_PARAMS = {
    "run_report": ["property_id", "date_ranges", "dimensions", "metrics"],
    "run_realtime_report": ["property_id", "dimensions", "metrics"],
    "run_conversions_report": [
        "property_id",
        "date_ranges",
        "dimensions",
        "metrics",
        "conversion_spec",
    ],
    "run_funnel_report": ["property_id", "funnel_steps"],
}

# run_funnel_report types three params dict[str, str] rather than
# dict[str, Any], so pydantic renders additionalProperties as a subschema
# ({"type": "string"}) instead of a boolean there. Verified: this has been
# true on the production HTTP path since fastmcp_app.py was created
# (2026-05-05) -- the coordinator.py sanitizer that "fixed" this only ever
# applied to the stdio path, and Claude Desktop moved onto the HTTP path
# (not the sanitized one) in 52e311d. Documented as a known exception rather
# than silently allowed everywhere: a NEW violation on any other tool still
# fails.
KNOWN_NON_BOOLEAN_ADDITIONAL_PROPERTIES = {
    "run_funnel_report",
}

HAS_COORDINATOR = (
    importlib.util.find_spec("analytics_mcp.coordinator") is not None
)


def fastmcp_tools() -> dict[str, dict]:
    """name -> full tool dict, as served over HTTP and (post-upgrade) stdio."""
    from analytics_mcp.fastmcp_app import mcp
    from fastmcp import Client

    async def _list() -> dict[str, dict]:
        async with Client(mcp) as client:
            return {
                # by_alias=True: mcp 2.x's Tool fields are snake_case
                # (input_schema); the wire, and this snapshot, stay
                # camelCase (inputSchema).
                t.name: t.model_dump(
                    mode="json", exclude_none=True, by_alias=True
                )
                for t in await client.list_tools()
            }

    return asyncio.run(_list())


def adk_tools() -> dict[str, dict]:
    """name -> tool dict on the pre-upgrade stdio path. Retires with coordinator."""
    # Deliberately imports a module this same migration deletes: only ever
    # called from tests gated behind `skipUnless(HAS_COORDINATOR, ...)`, so
    # it's dead code post-upgrade, not a live import mypy can resolve.
    import analytics_mcp.coordinator as coordinator  # type: ignore[import-not-found]

    return {
        t.name: t.model_dump(mode="json", exclude_none=True, by_alias=True)
        for t in coordinator.mcp_tools
    }


def walk(node: object) -> typing.Iterator[dict]:
    """Yields every dict in a JSON schema tree, node first."""
    if isinstance(node, dict):
        yield node
        for child in node.values():
            yield from walk(child)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


if typing.TYPE_CHECKING:
    # A real TestCase subclass would be picked up by unittest's own
    # discovery as an independent (and broken -- tools() raises) test class.
    # This is type-checking-only: mypy sees assertEqual/subTest/etc. on the
    # mixin body, but at runtime the mixin is a plain object, and only the
    # concrete FastMcpInvariantsTest/AdkInvariantsTest below are TestCases.
    _Base = unittest.TestCase
else:
    _Base = object


class _InvariantsMixin(_Base):
    """Subclassed once per stack so failures name the stack that broke."""

    def tools(self) -> dict[str, dict]:
        raise NotImplementedError

    def setUp(self) -> None:
        self.all_tools = self.tools()

    def test_inventory(self) -> None:
        """9 tools, these 9 names. Nothing added, renamed or dropped."""
        self.assertEqual(set(self.all_tools), TOOL_NAMES)

    def test_no_empty_input_schema(self) -> None:
        """Replaces coordinator's `if tool.inputSchema == {}` patch.

        Zero-arg tools (get_account_summaries) got a bare {} from ADK. Under
        MCP v2 an empty inputSchema fails result validation, so this is the
        one fixup that was actually load-bearing.
        """
        for name, tool in self.all_tools.items():
            with self.subTest(tool=name):
                schema = tool["inputSchema"]
                self.assertEqual(schema.get("type"), "object")
                self.assertIn("properties", schema)

    def test_additional_properties_is_boolean_except_known_cases(self) -> None:
        """Replaces coordinator's sanitize_mcp_schema_properties walker.

        Claude Desktop rejects a tool whose additionalProperties is a schema
        object rather than a boolean, at any depth. run_funnel_report is a
        documented, pre-existing exception (see
        KNOWN_NON_BOOLEAN_ADDITIONAL_PROPERTIES) -- everything else must be
        boolean.
        """
        for name, tool in self.all_tools.items():
            if name in KNOWN_NON_BOOLEAN_ADDITIONAL_PROPERTIES:
                continue
            for node in walk(tool["inputSchema"]):
                if "additionalProperties" in node:
                    with self.subTest(tool=name, node=sorted(node)):
                        self.assertIsInstance(
                            node["additionalProperties"], bool
                        )

    def test_no_null_type_beside_anyof(self) -> None:
        """Replaces coordinator's `anyOf` / "type": "null" deletion.

        `{"anyOf": [...], "type": "null"}` makes an optional param
        unfillable: every non-null value fails the sibling type check.
        """
        for name, tool in self.all_tools.items():
            for node in walk(tool["inputSchema"]):
                if "anyOf" in node:
                    with self.subTest(tool=name):
                        self.assertNotEqual(node.get("type"), "null")

    def test_required_params_on_reporting_tools(self) -> None:
        """Replaces coordinator's explicit `required` injection."""
        for name, expected in REQUIRED_PARAMS.items():
            with self.subTest(tool=name):
                self.assertEqual(
                    self.all_tools[name]["inputSchema"].get("required"),
                    expected,
                )

    def test_reporting_tools_keep_their_hint_blocks(self) -> None:
        """The long descriptions come from _run_*_description().

        Today fastmcp_app.py sources them from coordinator.tools. Once
        coordinator is gone, re-attaching them is a manual step that is very
        easy to forget -- and forgetting it silently strips ~12KB of
        worked-example hint text from production HTTP too, with no error
        anywhere.
        """
        for name in REQUIRED_PARAMS:
            with self.subTest(tool=name):
                description = self.all_tools[name]["description"]
                self.assertIn("Hints for arguments", description)
                self.assertGreater(len(description), 2000)


class FastMcpInvariantsTest(_InvariantsMixin, unittest.TestCase):
    def tools(self) -> dict[str, dict]:
        return fastmcp_tools()


@unittest.skipUnless(HAS_COORDINATOR, "coordinator.py removed by the upgrade")
class AdkInvariantsTest(_InvariantsMixin, unittest.TestCase):
    def tools(self) -> dict[str, dict]:
        return adk_tools()


@unittest.skipUnless(HAS_COORDINATOR, "coordinator.py removed by the upgrade")
class CrossStackTest(unittest.TestCase):
    """The honest bridge across the transition.

    Before the upgrade two stacks generate DIFFERENT schemas for the same
    nine tools (ADK emits no `title`; FastMCP emits `additionalProperties`/
    `outputSchema`/`_meta`). Asserting full equality would be a lie that
    forced someone to neuter the golden. So assert only the parts that must
    agree -- and let golden_tools_stdio.json carry the parts that
    legitimately change.
    """

    def setUp(self) -> None:
        self.adk = adk_tools()
        self.fastmcp = fastmcp_tools()

    def test_same_tool_names(self) -> None:
        self.assertEqual(set(self.adk), set(self.fastmcp))

    def test_same_descriptions(self) -> None:
        for name in self.adk:
            with self.subTest(tool=name):
                self.assertEqual(
                    self.adk[name]["description"],
                    self.fastmcp[name]["description"],
                )

    def test_same_required_and_parameter_names(self) -> None:
        for name in self.adk:
            with self.subTest(tool=name):
                adk_schema = self.adk[name]["inputSchema"]
                fm_schema = self.fastmcp[name]["inputSchema"]
                self.assertEqual(
                    adk_schema.get("required"), fm_schema.get("required")
                )
                self.assertEqual(
                    set(adk_schema.get("properties", {})),
                    set(fm_schema.get("properties", {})),
                )


if __name__ == "__main__":
    unittest.main()
