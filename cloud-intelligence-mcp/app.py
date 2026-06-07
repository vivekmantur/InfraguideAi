from mcp.server.fastmcp import FastMCP

from server.tools.pricing_tool import (
    register_pricing_tools
)

mcp = FastMCP(
    "cloud-intelligence-mcp"
)

register_pricing_tools(mcp)

if __name__ == "__main__":
    print("Starting MCP Server...")
    mcp.run(transport="streamable-http")