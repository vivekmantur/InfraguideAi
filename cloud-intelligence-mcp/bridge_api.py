from fastapi import FastAPI, Request
from mcp import ClientSession
from mcp.client.streamable_http import (
    streamablehttp_client
)

import json

app = FastAPI()


@app.middleware("http")
async def log_bridge_errors(
    request: Request,
    call_next
):

    try:

        return await call_next(
            request
        )

    except Exception as ex:

        print(
            f"Bridge API error for "
            f"{request.method} {request.url.path}:"
        )
        print(ex)
        raise


@app.post("/pricing/gcp")
async def get_gcp_pricing(
    payload: dict
):

    cpu = payload["cpu"]
    memory = payload["memory"]

    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp"
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

            print("MCP Result:")
            print(result)

            # -----------------------------
            # Case 1 : Structured response
            # -----------------------------
            if getattr(
                result,
                "structuredContent",
                None
            ):
                return result.structuredContent

            # -----------------------------
            # Case 2 : Text response
            # -----------------------------
            if (
                result.content
                and len(result.content) > 0
            ):

                text = result.content[0].text

                print("Raw MCP Text:")
                print(text)

                try:
                    return json.loads(text)

                except Exception as ex:

                    print(
                        "JSON Parse Error:"
                    )
                    print(ex)

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

    services = payload.get(
        "services",
        []
    )
    region = payload.get(
        "region",
        "us-central1"
    )

    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp"
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

            print("GCP Service MCP Result:")
            print(result)

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

    cpu = payload["cpu"]
    memory = payload["memory"]
    services = payload.get(
        "services",
        []
    )
    region = payload.get(
        "region"
    )
    limit = payload.get(
        "limit",
        10
    )

    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp"
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
                "get_gcp_regional_pricing",
                arguments={
                    "cpu": cpu,
                    "memory": memory,
                    "services": services,
                    "limit": limit,
                    "region": region
                }
            )

            print("GCP Regional MCP Result:")
            print(result)

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
                    "No content returned from GCP regional MCP"
            }
            
@app.post("/pricing/azure")
async def get_azure_pricing(
    payload: dict
):

    cpu = payload["cpu"]
    memory = payload["memory"]

    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp"
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

            print("Azure MCP Result:")
            print(result)

            # MCP SDK returns content not structuredContent

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

    services = payload.get(
        "services",
        []
    )
    region = payload.get(
        "region",
        "eastus"
    )

    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp"
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

            print("Azure Service MCP Result:")
            print(result)

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

    cpu = payload["cpu"]
    memory = payload["memory"]
    services = payload.get(
        "services",
        []
    )
    region = payload.get(
        "region"
    )
    limit = payload.get(
        "limit",
        10
    )

    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp"
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
                "get_azure_regional_pricing",
                arguments={
                    "cpu": cpu,
                    "memory": memory,
                    "services": services,
                    "limit": limit,
                    "region": region
                }
            )

            print("Azure Regional MCP Result:")
            print(result)

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
                    "No content returned from Azure regional MCP"
            }
