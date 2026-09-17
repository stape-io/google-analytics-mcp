import inspect

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from analytics_mcp.auth import get_auth_provider
from analytics_mcp.tools.admin.info import (
    get_account_summaries,
    get_property_details,
    list_google_ads_links,
    list_property_annotations,
)
from analytics_mcp.tools.reporting.conversions import (
    _run_conversions_report_description,
    run_conversions_report,
)
from analytics_mcp.tools.reporting.core import (
    _run_report_description,
    run_report,
)
from analytics_mcp.tools.reporting.funnel import (
    _run_funnel_report_description,
    run_funnel_report,
)
from analytics_mcp.tools.reporting.metadata import (
    get_custom_dimensions_and_metrics,
)
from analytics_mcp.tools.reporting.realtime import (
    _run_realtime_report_description,
    run_realtime_report,
)

# Every tool passes an explicit description rather than letting FastMCP
# derive one from the docstring. FastMCP's own parsing would strip the
# `Args:` block into per-property schema descriptions instead -- a real
# improvement, but a model-facing change to 3 tools' descriptions that
# deserves its own reviewable PR, not a side effect of this migration.
# inspect.getdoc(fn) reproduces the previous (ADK-derived) description
# byte-for-byte for the 5 tools that don't have a dedicated hint function;
# the other 4 already build a long, hint-laden description of their own.
tools = [
    FunctionTool.from_function(
        get_account_summaries,
        description=inspect.getdoc(get_account_summaries),
    ),
    FunctionTool.from_function(
        list_google_ads_links,
        description=inspect.getdoc(list_google_ads_links),
    ),
    FunctionTool.from_function(
        get_property_details,
        description=inspect.getdoc(get_property_details),
    ),
    FunctionTool.from_function(
        list_property_annotations,
        description=inspect.getdoc(list_property_annotations),
    ),
    FunctionTool.from_function(
        get_custom_dimensions_and_metrics,
        description=inspect.getdoc(get_custom_dimensions_and_metrics),
    ),
    FunctionTool.from_function(
        run_report, description=_run_report_description()
    ),
    FunctionTool.from_function(
        run_realtime_report, description=_run_realtime_report_description()
    ),
    FunctionTool.from_function(
        run_funnel_report, description=_run_funnel_report_description()
    ),
    FunctionTool.from_function(
        run_conversions_report,
        description=_run_conversions_report_description(),
    ),
]

mcp = FastMCP(
    "Google Analytics MCP Server", tools=tools, auth=get_auth_provider()
)
