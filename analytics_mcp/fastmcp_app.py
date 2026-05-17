from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from analytics_mcp.auth import get_auth_provider
from analytics_mcp.coordinator import tools as analytics_tools

tools = [
    FunctionTool.from_function(tool.func, name=tool.name, description=tool.description)
    for tool in analytics_tools
]
mcp = FastMCP(
    "Google Analytics MCP Server",
    tools=tools,
    auth=get_auth_provider()
)
