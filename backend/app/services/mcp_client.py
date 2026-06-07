import httpx


class CloudMcpClient:

    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"

    async def get_pricing(
        self,
        cpu: int,
        memory: int,
        storage: int,
        provider: str
    ):

        payload = {
            "cpu": cpu,
            "memory": memory,
            "storage": storage,
            "provider": provider
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mcp/tools/compare_cloud_costs",
                json=payload
            )

            return response.json()