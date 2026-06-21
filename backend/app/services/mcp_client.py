import os

import httpx

def _without_none(payload: dict) -> dict:
    """Return a payload copy without keys whose values are None.

    Args:
        payload: Request payload that may contain optional values.

    Returns:
        A dictionary containing only keys with non-None values.
    """
    return {
        key: value
        for key, value in payload.items()
        if value is not None
    }

class CloudMcpClient:
    """HTTP client for the local cloud intelligence bridge."""

    def __init__(self):
        """Initialize the bridge base URL from environment configuration.

        Returns:
            None.
        """

        self.base_url = os.getenv(
            "MCP_BRIDGE_URL",
            "http://127.0.0.1:8001"
        ).rstrip("/")

    async def get_gcp_compute_pricing(
        self,
        cpu: int,
        memory: int
    ) -> dict:
        """Fetch GCP compute pricing for a CPU and memory shape.

        Args:
            cpu: Requested vCPU count.
            memory: Requested memory in GB.

        Returns:
            Pricing response from the MCP bridge.
        """

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
        """Fetch Azure VM pricing for a CPU and memory shape.

        Args:
            cpu: Requested vCPU count.
            memory: Requested memory in GB.

        Returns:
            Pricing response from the MCP bridge.
        """

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
        """Fetch GCP managed service pricing for a region.

        Args:
            services: Recommended services to price.
            region: GCP region for the pricing lookup.

        Returns:
            Managed service pricing response from the MCP bridge.
        """

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
        """Fetch GCP regional runtime and service pricing rows.

        Args:
            cpu: Requested vCPU count.
            memory: Requested memory in GB.
            services: Recommended services to include in regional totals.
            limit: Maximum number of regions to return.
            region: Optional single region to price.

        Returns:
            Regional pricing response from the MCP bridge.
        """

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
        """Fetch Azure managed service pricing for a region.

        Args:
            services: Recommended services to price.
            region: Azure region for the pricing lookup.

        Returns:
            Managed service pricing response from the MCP bridge.
        """

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
        """Fetch Azure regional runtime and service pricing rows.

        Args:
            cpu: Requested vCPU count.
            memory: Requested memory in GB.
            services: Recommended services to include in regional totals.
            limit: Maximum number of regions to return.
            region: Optional single region to price.

        Returns:
            Regional pricing response from the MCP bridge.
        """

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
        """Fetch AWS regional runtime and service pricing rows.

        Args:
            cpu: Requested vCPU count.
            memory: Requested memory in GB.
            services: Recommended services to include in regional totals.
            limit: Maximum number of regions to return.
            region: Optional single region to price.

        Returns:
            Regional pricing response from the MCP bridge.
        """

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
        """Check whether the cloud intelligence bridge is reachable.

        Returns:
            Health response from the MCP bridge.
        """

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
        """Check provider service availability for a target region.

        Args:
            provider: Cloud provider name.
            region: Cloud region to validate.
            services: Services that should be checked for availability.

        Returns:
            Service availability response from the MCP bridge.
        """

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
        """Check whether a target service supports detected runtimes.

        Args:
            provider: Cloud provider name.
            target_service: Recommended runtime service.
            runtimes: Detected application runtimes.
            frameworks: Optional detected application frameworks.

        Returns:
            Runtime support response from the MCP bridge.
        """

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
        """Fetch limit metadata for a cloud provider service.

        Args:
            provider: Cloud provider name.
            service: Provider service name.

        Returns:
            Service limits response from the MCP bridge.
        """

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
