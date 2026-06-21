import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from mcp import ClientSession
from mcp.client.streamable_http import (
    streamablehttp_client
)

def _prefer_project_venv_packages() -> None:
    """Prefer packages installed in the project virtual environment.
    
    Returns:
        Prefer project venv packages result.
    """
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

app = FastAPI()

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://127.0.0.1:8000/mcp"
)

async def call_mcp_tool(
    tool_name: str,
    arguments: dict | None = None
) -> dict:
    """Call an MCP tool through the configured bridge process.
    
    Args:
        tool_name: tool name value.
        arguments: arguments value.
    
    Returns:
        Call mcp tool result.
    """
    clean_arguments = {
        key: value
        for key, value in (arguments or {}).items()
        if value is not None
    }

    async with streamablehttp_client(
        MCP_SERVER_URL
    ) as (
        read_stream,
        write_stream,
        _
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments=clean_arguments
            )

            if getattr(
                result,
                "structuredContent",
                None
            ):
                return result.structuredContent

            if (
                result.content
                and len(result.content) > 0
            ):
                text = result.content[0].text

                try:
                    return json.loads(text)

                except Exception as ex:
                    return {
                        "error": text,
                        "parse_error": str(ex),
                    }

            return {
                "error":
                    f"No content returned from MCP tool {tool_name}"
            }

@app.middleware("http")
async def log_bridge_errors(
    request: Request,
    call_next
):

    """Log bridge errors and return an HTTP error response.
    
    Args:
        request: request value.
        call_next: call next value.
    
    Returns:
        Result produced by log bridge errors.
    """
    try:

        return await call_next(
            request
        )

    except Exception as ex:
        raise

@app.post("/pricing/gcp")
async def get_gcp_pricing(
    payload: dict
):

    """Return GCP compute pricing for the requested shape.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get gcp pricing.
    """
    cpu = payload["cpu"]
    memory = payload["memory"]

    async with streamablehttp_client(
        MCP_SERVER_URL
    ) as (
        read_stream,
        write_stream,
        _
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            print("Calling MCP Tool...")

            result = await session.call_tool(
                "get_gcp_compute_pricing",
                arguments={
                    "cpu": cpu,
                    "memory": memory
                }
            )
            if getattr(
                result,
                "structuredContent",
                None
            ):
                return result.structuredContent

            if (
                result.content
                and len(result.content) > 0
            ):

                text = result.content[0].text

                try:
                    return json.loads(text)

                except Exception as ex:
                    return {
                        "error":
                            f"Unable to parse MCP response: {str(ex)}"
                    }

            return {
                "error":
                    "No content returned from MCP"
            }

@app.post("/pricing/gcp/services")
async def get_gcp_service_pricing(
    payload: dict
):

    """Return GCP managed service pricing for requested services.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get gcp service pricing.
    """
    services = payload.get(
        "services",
        []
    )
    region = payload.get(
        "region",
        "us-central1"
    )

    async with streamablehttp_client(
        MCP_SERVER_URL
    ) as (
        read_stream,
        write_stream,
        _
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                "get_gcp_service_pricing",
                arguments={
                    "services": services,
                    "region": region
                }
            )
            if getattr(
                result,
                "structuredContent",
                None
            ):
                return result.structuredContent

            if (
                result.content
                and len(result.content) > 0
            ):

                text = result.content[0].text

                try:
                    return json.loads(text)

                except Exception as ex:

                    return {
                        "error":
                            f"Unable to parse MCP response: {str(ex)}"
                    }

            return {
                "error":
                    "No content returned from GCP service MCP"
            }

@app.post("/pricing/gcp/regions")
async def get_gcp_regional_pricing(
    payload: dict
):

    """Return GCP regional runtime and service pricing.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get gcp regional pricing.
    """
    return await call_mcp_tool(
        "get_gcp_regional_pricing",
        {
            "cpu": payload["cpu"],
            "memory": payload["memory"],
            "services": payload.get(
                "services",
                []
            ),
            "limit": payload.get(
                "limit",
                10
            ),
            "region": payload.get(
                "region"
            )
        }
    )

@app.post("/pricing/azure")
async def get_azure_pricing(
    payload: dict
):

    """Return Azure VM pricing for the requested shape.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get azure pricing.
    """
    cpu = payload["cpu"]
    memory = payload["memory"]

    async with streamablehttp_client(
        MCP_SERVER_URL
    ) as (
        read_stream,
        write_stream,
        _
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                "get_azure_vm_pricing",
                arguments={
                    "cpu": cpu,
                    "memory": memory
                }
            )
            if result.content:

                import json

                text = result.content[0].text

                try:
                    return json.loads(text)

                except Exception:

                    return {
                        "error": text
                    }

            return {
                "error":
                    "No content returned from Azure MCP"
            }


@app.post("/pricing/azure/services")
async def get_azure_service_pricing(
    payload: dict
):

    """Return Azure managed service pricing for requested services.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get azure service pricing.
    """
    services = payload.get(
        "services",
        []
    )
    region = payload.get(
        "region",
        "eastus"
    )

    async with streamablehttp_client(
        MCP_SERVER_URL
    ) as (
        read_stream,
        write_stream,
        _
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                "get_azure_service_pricing",
                arguments={
                    "services": services,
                    "region": region
                }
            )
            if result.content:

                text = result.content[0].text

                try:
                    return json.loads(text)

                except Exception:

                    return {
                        "error": text
                    }

            return {
                "error":
                    "No content returned from Azure service MCP"
            }

@app.post("/pricing/azure/regions")
async def get_azure_regional_pricing(
    payload: dict
):

    """Return Azure regional runtime and service pricing.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get azure regional pricing.
    """
    return await call_mcp_tool(
        "get_azure_regional_pricing",
        {
            "cpu": payload["cpu"],
            "memory": payload["memory"],
            "services": payload.get(
                "services",
                []
            ),
            "limit": payload.get(
                "limit",
                10
            ),
            "region": payload.get(
                "region"
            )
        }
    )

@app.post("/pricing/aws/regions")
async def get_aws_regional_pricing(
    payload: dict
):

    """Return AWS regional runtime and service pricing.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get aws regional pricing.
    """
    return await call_mcp_tool(
        "get_aws_regional_pricing",
        {
            "cpu": payload["cpu"],
            "memory": payload["memory"],
            "services": payload.get(
                "services",
                []
            ),
            "limit": payload.get(
                "limit",
                10
            ),
            "region": payload.get(
                "region"
            )
        }
    )

@app.get("/cloud-intelligence/health")
async def cloud_intelligence_health():
    """Return cloud intelligence health information.
    
    Returns:
        Result produced by cloud intelligence health.
    """
    return await call_mcp_tool(
        "health_check_cloud_intelligence"
    )

@app.post("/cloud-intelligence/service-availability")
async def check_service_availability(
    payload: dict
):
    """Check service availability for a cloud provider and region.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by check service availability.
    """
    return await call_mcp_tool(
        "check_service_availability",
        {
            "provider": payload["provider"],
            "region": payload["region"],
            "services": payload.get(
                "services",
                []
            )
        }
    )

@app.post("/cloud-intelligence/runtime-support")
async def check_runtime_support(
    payload: dict
):
    """Check runtime support for a provider service.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by check runtime support.
    """
    return await call_mcp_tool(
        "check_runtime_support",
        {
            "provider": payload["provider"],
            "target_service": payload["target_service"],
            "runtimes": payload.get(
                "runtimes",
                []
            ),
            "frameworks": payload.get(
                "frameworks",
                []
            )
        }
    )

@app.post("/cloud-intelligence/service-limits")
async def get_service_limits(
    payload: dict
):
    """Return service limit metadata for a provider service.
    
    Args:
        payload: payload value.
    
    Returns:
        Result produced by get service limits.
    """
    return await call_mcp_tool(
        "get_service_limits",
        {
            "provider": payload["provider"],
            "service": payload["service"]
        }
    )
