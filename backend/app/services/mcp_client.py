import httpx


class CloudMcpClient:

    def __init__(self):

        self.base_url = (
            "http://127.0.0.1:8001"
        )

    async def get_gcp_compute_pricing(
        self,
        cpu: int,
        memory: int
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=120
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/gcp",
                json={
                    "cpu": cpu,
                    "memory": memory
                }
            )

            response.raise_for_status()

            return response.json()
        
    async def get_azure_vm_pricing(
        self,
        cpu: int,
        memory: int
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/azure",
                json={
                    "cpu": cpu,
                    "memory": memory
                }
            )

            response.raise_for_status()

            return response.json()