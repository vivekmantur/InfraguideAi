import os

import httpx


def _without_none(payload: dict) -> dict:
    return {
        key: value
        for key, value in payload.items()
        if value is not None
    }


class CloudMcpClient:

    def __init__(self):

        self.base_url = os.getenv(
            "MCP_BRIDGE_URL",
            "http://127.0.0.1:8001"
        ).rstrip("/")

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

    async def get_gcp_service_pricing(
        self,
        services: list[dict],
        region: str = "us-central1"
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=120
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/gcp/services",
                json={
                    "services": services,
                    "region": region
                }
            )

            response.raise_for_status()

            return response.json()

    async def get_gcp_regional_pricing(
        self,
        cpu: int,
        memory: int,
        services: list[dict],
        limit: int = 10,
        region: str | None = None
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=240
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/gcp/regions",
                json=_without_none({
                    "cpu": cpu,
                    "memory": memory,
                    "services": services,
                    "limit": limit,
                    "region": region
                })
            )

            response.raise_for_status()

            return response.json()

    async def get_azure_service_pricing(
        self,
        services: list[dict],
        region: str = "eastus"
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/azure/services",
                json={
                    "services": services,
                    "region": region
                }
            )

            response.raise_for_status()

            return response.json()

    async def get_azure_regional_pricing(
        self,
        cpu: int,
        memory: int,
        services: list[dict],
        limit: int = 10,
        region: str | None = None
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=240
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/azure/regions",
                json=_without_none({
                    "cpu": cpu,
                    "memory": memory,
                    "services": services,
                    "limit": limit,
                    "region": region
                })
            )

            response.raise_for_status()

            return response.json()

    async def get_aws_regional_pricing(
        self,
        cpu: int,
        memory: int,
        services: list[dict],
        limit: int = 10,
        region: str | None = None
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=240
        ) as client:

            response = await client.post(
                f"{self.base_url}/pricing/aws/regions",
                json=_without_none({
                    "cpu": cpu,
                    "memory": memory,
                    "services": services,
                    "limit": limit,
                    "region": region
                })
            )

            response.raise_for_status()

            return response.json()

    async def health_check_cloud_intelligence(
        self
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                f"{self.base_url}/cloud-intelligence/health"
            )

            response.raise_for_status()

            return response.json()

    async def check_service_availability(
        self,
        provider: str,
        region: str,
        services: list[dict]
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(
                f"{self.base_url}/cloud-intelligence/service-availability",
                json={
                    "provider": provider,
                    "region": region,
                    "services": services
                }
            )

            response.raise_for_status()

            return response.json()

    async def check_runtime_support(
        self,
        provider: str,
        target_service: str,
        runtimes: list[str],
        frameworks: list[str] | None = None
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(
                f"{self.base_url}/cloud-intelligence/runtime-support",
                json={
                    "provider": provider,
                    "target_service": target_service,
                    "runtimes": runtimes,
                    "frameworks": frameworks or []
                }
            )

            response.raise_for_status()

            return response.json()

    async def get_service_limits(
        self,
        provider: str,
        service: str
    ) -> dict:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(
                f"{self.base_url}/cloud-intelligence/service-limits",
                json={
                    "provider": provider,
                    "service": service
                }
            )

            response.raise_for_status()

            return response.json()
