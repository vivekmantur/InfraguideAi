import os
import sys
from pathlib import Path


def _prefer_project_venv_packages() -> None:
    project_dir = Path(__file__).resolve().parent
    site_packages = (
        project_dir / ".venv" / "Lib" / "site-packages"
        if os.name == "nt"
        else project_dir
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )

    if not site_packages.exists():
        return

    site_packages_path = str(site_packages)
    if site_packages_path not in sys.path:
        sys.path.insert(0, site_packages_path)


_prefer_project_venv_packages()

from mcp.server.fastmcp import FastMCP

from server.tools.cloud_intelligence_tool import (
    register_cloud_intelligence_tools
)
from server.tools.pricing_tool import (
    register_pricing_tools
)

mcp = FastMCP(
    "cloud-intelligence-mcp"
)

register_pricing_tools(mcp)
register_cloud_intelligence_tools(mcp)

if __name__ == "__main__":
    print("Starting MCP Server...")
    mcp.run(transport="streamable-http")
