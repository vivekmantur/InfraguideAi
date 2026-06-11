import httpx


class AzurePricingClient:

    BASE_URL = (
        "https://prices.azure.com/api/retail/prices"
    )

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

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(
                self.BASE_URL,
                params={
                    "$filter": filter_query
                }
            )

            response.raise_for_status()

            data = response.json()

            items = data.get(
                "Items",
                []
            )

            if not items:

                raise ValueError(
                    f"No pricing found for "
                    f"{vm_sku} in {region}"
                )

            #
            # Prefer normal Consumption pricing
            # Ignore Spot, Low Priority,
            # Reservations, DevTest
            #
            price_item = next(
                (
                    item
                    for item in items
                    if (
                        item.get("type")
                        == "Consumption"
                    )
                    and (
                        item.get(
                            "isPrimaryMeterRegion",
                            False
                        )
                    )
                    and (
                        "Spot"
                        not in item.get(
                            "skuName",
                            ""
                        )
                    )
                    and (
                        "Low Priority"
                        not in item.get(
                            "skuName",
                            ""
                        )
                    )
                ),
                items[0]
            )

            hourly_cost = (
                price_item.get(
                    "retailPrice",
                    0
                )
            )

            monthly_cost = (
                hourly_cost
                * 24
                * 30
            )

            return {
                "provider": "Azure",
                "service": "Virtual Machine",
                "sku": vm_sku,
                "region": region,
                "currency": price_item.get(
                    "currencyCode",
                    "USD"
                ),
                "hourly_cost": round(
                    hourly_cost,
                    6
                ),
                "monthly_cost": round(
                    monthly_cost,
                    2
                ),
                "product_name": price_item.get(
                    "productName"
                ),
                "meter_name": price_item.get(
                    "meterName"
                ),
                "effective_date": price_item.get(
                    "effectiveStartDate"
                )
            }