from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.streamable_http import (
    streamablehttp_client
)

import json

app = FastAPI()


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