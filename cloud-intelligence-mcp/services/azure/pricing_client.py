import httpx


class AzurePricingClient:

    BASE_URL = (
        "https://prices.azure.com/api/retail/prices"
    )

    SERVICE_RULES = [
        {
            "match": "SQL Database",
            "service_name": "SQL Database",
            "quantity": 730,
            "unit": "vCore-hours/month",
            "required_terms": [
                "vCore"
            ],
            "fallback_monthly": 110,
        },
        {
            "match": "PostgreSQL",
            "service_name": "Azure Database for PostgreSQL",
            "quantity": 730,
            "unit": "vCore-hours/month",
            "required_terms": [
                "vCore"
            ],
            "fallback_monthly": 95,
        },
        {
            "match": "Blob Storage",
            "service_name": "Storage",
            "quantity": 50,
            "unit": "GB-month",
            "required_terms": [
                "Data Stored"
            ],
            "preferred_terms": [
                "Hot",
                "LRS"
            ],
            "fallback_monthly": 2,
        },
        {
            "match": "Key Vault",
            "service_name": "Key Vault",
            "quantity": 10,
            "unit": "10k operations/month",
            "required_terms": [
                "Operations"
            ],
            "fallback_monthly": 1,
        },
        {
            "match": "Azure Monitor",
            "service_name": "Azure Monitor",
            "quantity": 5,
            "unit": "GB ingested/month",
            "required_terms": [
                "Data Ingestion"
            ],
            "fallback_monthly": 15,
        },
    ]

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

    async def get_service_prices(
        self,
        region: str,
        services: list[dict]
    ) -> dict:

        line_items: list[str] = []
        assumptions: list[str] = []
        items: list[dict] = []
        monthly_total = 0.0
        currency = "USD"

        for service in services:

            recommended = service.get(
                "recommended",
                ""
            )
            component = service.get(
                "component",
                recommended
            )

            rule = self._find_rule(
                recommended
            )

            if not rule:

                continue

            estimate = await self._estimate_service_price(
                region,
                recommended,
                rule
            )

            monthly_total += estimate["monthly_cost"]
            currency = estimate.get(
                "currency",
                currency
            )

            items.append(
                {
                    "component": component,
                    "recommended": recommended,
                    **estimate
                }
            )
            line_items.append(
                (
                    f"{component}: {recommended} "
                    f"({estimate['quantity']} {estimate['unit']}): "
                    f"{estimate['currency']} "
                    f"{estimate['monthly_cost']:.2f}/month"
                )
            )
            assumptions.append(
                (
                    f"{recommended}: estimated with "
                    f"{estimate['quantity']} {estimate['unit']} "
                    f"using {estimate['source']}."
                )
            )

        return {
            "provider": "Azure",
            "region": region,
            "currency": currency,
            "monthly_cost": round(
                monthly_total,
                2
            ),
            "line_items": line_items,
            "assumptions": assumptions,
            "items": items
        }

    def _find_rule(
        self,
        recommended: str
    ) -> dict | None:

        for rule in self.SERVICE_RULES:

            if rule["match"] in recommended:

                return rule

        return None

    async def _estimate_service_price(
        self,
        region: str,
        recommended: str,
        rule: dict
    ) -> dict:

        try:

            price_item = await self._get_retail_price_item(
                region,
                rule
            )

        except Exception as ex:

            return {
                "currency": "USD",
                "monthly_cost": float(
                    rule["fallback_monthly"]
                ),
                "quantity": rule["quantity"],
                "unit": rule["unit"],
                "source": (
                    "baseline fallback because Azure Retail "
                    f"Pricing lookup failed: {str(ex)}"
                ),
                "meter_name": None,
                "product_name": recommended,
            }

        unit_price = price_item.get(
            "retailPrice",
            0
        )
        monthly_cost = (
            unit_price
            * rule["quantity"]
        )

        return {
            "currency": price_item.get(
                "currencyCode",
                "USD"
            ),
            "monthly_cost": round(
                monthly_cost,
                2
            ),
            "quantity": rule["quantity"],
            "unit": rule["unit"],
            "source": "Azure Retail Pricing API",
            "meter_name": price_item.get(
                "meterName"
            ),
            "product_name": price_item.get(
                "productName"
            ),
            "sku_name": price_item.get(
                "skuName"
            ),
            "effective_date": price_item.get(
                "effectiveStartDate"
            )
        }

    async def _get_retail_price_item(
        self,
        region: str,
        rule: dict
    ) -> dict:

        filter_query = (
            f"serviceName eq '{rule['service_name']}' "
            f"and armRegionName eq '{region}'"
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
                f"{rule['service_name']} in {region}"
            )

        required_terms = rule.get(
            "required_terms",
            []
        )
        preferred_terms = rule.get(
            "preferred_terms",
            []
        )

        candidates = [
            item
            for item in items
            if item.get("type") == "Consumption"
            and all(
                self._item_contains(
                    item,
                    term
                )
                for term in required_terms
            )
        ]

        if not candidates:

            raise ValueError(
                f"No consumption meter matched "
                f"{rule['service_name']}"
            )

        preferred = [
            item
            for item in candidates
            if all(
                self._item_contains(
                    item,
                    term
                )
                for term in preferred_terms
            )
        ]

        return (
            preferred[0]
            if preferred
            else candidates[0]
        )

    def _item_contains(
        self,
        item: dict,
        term: str
    ) -> bool:

        haystack = " ".join(
            str(
                item.get(
                    field,
                    ""
                )
            )
            for field in (
                "serviceName",
                "productName",
                "skuName",
                "meterName"
            )
        )

        return term.lower() in haystack.lower()
