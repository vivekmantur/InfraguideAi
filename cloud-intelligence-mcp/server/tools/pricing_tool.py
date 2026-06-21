from config import GCP_API_KEY
from services.azure.pricing_client import AzurePricingClient
from services.aws.pricing_client import AwsPricingClient
from services.gcp.pricing_client import GcpPricingClient
from services.pricing_cache import pricing_cache
from services.azure.sku_selector import (
    select_vm_size
)

if not GCP_API_KEY:
    raise ValueError(
        "GCP_API_KEY not found!"
    )

azure_client = AzurePricingClient()
aws_client = AwsPricingClient()

gcp_client = GcpPricingClient(
    api_key=GCP_API_KEY
)

def register_pricing_tools(mcp):
    """Register pricing MCP tools on the server.

    Args:
        mcp: MCP server instance that receives tool registrations.

    Returns:
        None.
    """

    @mcp.tool()
    async def get_azure_vm_pricing(
        cpu: int,
        memory: int,
        region: str = "eastus"
    ) -> dict:

        """Get azure vm pricing.
        
        Args:
            cpu: cpu value.
            memory: memory value.
            region: region value.
        
        Returns:
            Get azure vm pricing result.
        """
        try:

            vm_sku = select_vm_size(
                cpu,
                memory
            )

            result = await azure_client.get_vm_price(
                region,
                vm_sku
            )

            return result

        except Exception as ex:
            return {
                "provider": "Azure",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_gcp_compute_pricing(
        cpu: int,
        memory: int
    ) -> dict:

        """Get gcp compute pricing.
        
        Args:
            cpu: cpu value.
            memory: memory value.
        
        Returns:
            Get gcp compute pricing result.
        """
        try:

            result = await gcp_client.get_compute_price(
                cpu,
                memory
            )

            return result

        except Exception as ex:
            return {
                "provider": "GCP",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_gcp_service_pricing(
        services: list,
        region: str = "us-central1"
    ) -> dict:

        """Return GCP managed service pricing for requested services.
        
        Args:
            services: services value.
            region: region value.
        
        Returns:
            Get gcp service pricing result.
        """
        try:

            result = await gcp_client.get_service_prices(
                region,
                services
            )
            return result

        except Exception as ex:
            return {
                "provider": "GCP",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_azure_service_pricing(
        services: list,
        region: str = "eastus"
    ) -> dict:

        """Return Azure managed service pricing for requested services.
        
        Args:
            services: services value.
            region: region value.
        
        Returns:
            Get azure service pricing result.
        """
        try:

            result = await azure_client.get_service_prices(
                region,
                services
            )
            return result

        except Exception as ex:

            return {
                "provider": "Azure",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_azure_regional_pricing(
        cpu: int,
        memory: int,
        services: list,
        limit: int = 10,
        region: str = None
    ) -> dict:

        """Return Azure regional runtime and service pricing.
        
        Args:
            cpu: cpu value.
            memory: memory value.
            services: services value.
            limit: limit value.
            region: region value.
        
        Returns:
            Get azure regional pricing result.
        """
        try:

            vm_sku = select_vm_size(
                cpu,
                memory
            )

            result = await azure_client.get_regional_prices(
                vm_sku,
                services,
                limit,
                region
            )
            return result

        except Exception as ex:
            return {
                "provider": "Azure",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_gcp_regional_pricing(
        cpu: int,
        memory: int,
        services: list,
        limit: int = 10,
        region: str = None
    ) -> dict:

        """Return GCP regional runtime and service pricing.
        
        Args:
            cpu: cpu value.
            memory: memory value.
            services: services value.
            limit: limit value.
            region: region value.
        
        Returns:
            Get gcp regional pricing result.
        """
        try:

            result = await gcp_client.get_regional_prices(
                cpu,
                memory,
                services,
                limit,
                region
            )

            return result

        except Exception as ex:

            return {
                "provider": "GCP",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_aws_regional_pricing(
        cpu: int,
        memory: int,
        services: list,
        limit: int = 10,
        region: str = None
    ) -> dict:

        """Return AWS regional runtime and service pricing.
        
        Args:
            cpu: cpu value.
            memory: memory value.
            services: services value.
            limit: limit value.
            region: region value.
        
        Returns:
            Get aws regional pricing result.
        """
        try:

            result = await pricing_cache.get_or_set(
                "aws:regional_pricing",
                {
                    "cpu": cpu,
                    "memory": memory,
                    "services": services,
                    "limit": limit,
                    "region": region
                },
                lambda: _get_aws_regional_pricing(
                    cpu,
                    memory,
                    services,
                    limit,
                    region
                )
            )
            return result

        except Exception as ex:

            return {
                "provider": "AWS",
                "error": str(ex)
            }

async def _get_aws_regional_pricing(
    cpu: int,
    memory: int,
    services: list[dict],
    limit: int,
    region: str | None
) -> dict:
    """Get aws regional pricing.
    
    Args:
        cpu: cpu value.
        memory: memory value.
        services: services value.
        limit: limit value.
        region: region value.
    
    Returns:
        Get aws regional pricing result.
    """
    return aws_client.regional_pricing(
        cpu=cpu,
        memory=memory,
        services=services,
        limit=limit,
        region=region
    )
