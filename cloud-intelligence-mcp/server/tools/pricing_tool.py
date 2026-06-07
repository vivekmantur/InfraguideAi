from services.azure.pricing_client import AzurePricingClient

azure_client = AzurePricingClient()


def register_pricing_tools(mcp):

    @mcp.tool()
    async def get_azure_vm_pricing(
        region: str,
        vm_sku: str
    ) -> dict:
        """
        Retrieve Azure VM pricing.

        Example:
        region = eastus
        vm_sku = Standard_D4s_v5
        """

        result = await azure_client.get_vm_price(
            region,
            vm_sku
        )

        result["monthly_cost"] = (
            result["hourly_cost"] * 24 * 30
        )

        return result