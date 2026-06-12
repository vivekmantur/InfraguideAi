from config import GCP_API_KEY

from services.azure.pricing_client import AzurePricingClient
from services.gcp.pricing_client import GcpPricingClient
from services.azure.sku_selector import (
    select_vm_size
)

if not GCP_API_KEY:
    raise ValueError(
        "GCP_API_KEY not found in .env"
    )

azure_client = AzurePricingClient()

gcp_client = GcpPricingClient(
    api_key=GCP_API_KEY
)

def register_pricing_tools(mcp):

    @mcp.tool()
    async def get_azure_vm_pricing(
        cpu: int,
        memory: int,
        region: str = "eastus"
    ) -> dict:

        try:

            vm_sku = select_vm_size(
                cpu,
                memory
            )

            result = await azure_client.get_vm_price(
                region,
                vm_sku
            )

            print("Azure Pricing Result:")
            print(result)

            return result

        except Exception as ex:

            print("Azure Pricing Error:")
            print(ex)

            return {
                "provider": "Azure",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_gcp_compute_pricing(
        cpu: int,
        memory: int
    ) -> dict:

        print(
            f"Pricing request received: "
            f"cpu={cpu}, memory={memory}"
        )

        try:

            result = await gcp_client.get_compute_price(
                cpu,
                memory
            )

            print("Pricing result:")
            print(result)

            return result

        except Exception as ex:

            print("Pricing error:")
            print(ex)

            return {
                "provider": "GCP",
                "error": str(ex)
            }

    @mcp.tool()
    async def get_gcp_service_pricing(
        services: list[dict],
        region: str = "us-central1"
    ) -> dict:

        try:

            result = await gcp_client.get_service_prices(
                region,
                services
            )

            print("GCP Service Pricing Result:")
            print(result)

            return result

        except Exception as ex:

            print("GCP Service Pricing Error:")
            print(ex)

            return {
                "provider": "GCP",
                "error": str(ex)
            }
