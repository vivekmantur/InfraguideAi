import httpx


class AzurePricingClient:

    BASE_URL = "https://prices.azure.com/api/retail/prices"

    async def get_vm_price(
        self,
        region: str,
        vm_sku: str
    ) -> dict:

        filter_query = (
            f"serviceName eq 'Virtual Machines' "
            f"and armRegionName eq '{region}' "
            f"and armSkuName eq '{vm_sku}'"
        )

        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.get(
                self.BASE_URL,
                params={
                    "$filter": filter_query
                }
            )

            response.raise_for_status()

            data = response.json()

            items = data.get("Items", [])

            if not items:
                raise ValueError(
                    f"No pricing found for {vm_sku} in {region}"
                )

            first = items[0]

            return {
                "provider": "Azure",
                "service": "Virtual Machine",
                "sku": vm_sku,
                "region": region,
                "hourly_cost": first.get("retailPrice", 0)
            }