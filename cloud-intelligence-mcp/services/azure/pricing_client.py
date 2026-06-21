import asyncio
import httpx
from services.pricing_cache import pricing_cache

class AzurePricingClient:

    """Client for retrieving Azure retail pricing data.
    
    """
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

        """Get vm price.
        
        Args:
            region: region value.
            vm_sku: vm sku value.
        
        Returns:
            Get vm price result.
        """
        filter_query = (
            f"serviceName eq 'Virtual Machines' "
            f"and armRegionName eq '{region}' "
            f"and armSkuName eq '{vm_sku}'"
        )

        items = await self._get_retail_items(
            filter_query
        )

        if not items:

            raise ValueError(
                f"No pricing found for "
                f"{vm_sku} in {region}"
            )
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

    async def get_regional_prices(
        self,
        vm_sku: str,
        services: list[dict],
        limit: int = 10,
        region: str | None = None
    ) -> dict:

        """Get regional prices.
        
        Args:
            vm_sku: vm sku value.
            services: services value.
            limit: limit value.
            region: region value.
        
        Returns:
            Get regional prices result.
        """
        if region:
            vm_prices = [
                await self.get_vm_price(
                    region,
                    vm_sku
                )
            ]

        else:
            vm_prices = (
                await self.get_vm_prices_by_region(
                vm_sku
                )
            )[:limit]
        semaphore = asyncio.Semaphore(8)

        async def build_row(
            vm_price: dict
        ) -> dict:

            """Build row.
            
            Args:
                vm_price: vm price value.
            
            Returns:
                Build row result.
            """
            async with semaphore:

                service_prices = await self.get_service_prices(
                    vm_price["region"],
                    services
                )

            service_monthly = service_prices.get(
                "monthly_cost",
                0
            )
            service_breakdown = [
                {
                    "component": item.get(
                        "component",
                        "Service"
                    ),
                    "recommended": item.get(
                        "recommended",
                        ""
                    ),
                    "monthly_cost": item.get(
                        "monthly_cost",
                        0
                    ),
                    "currency": item.get(
                        "currency",
                        service_prices.get(
                            "currency",
                            "USD"
                        )
                    ),
                    "source": item.get(
                        "source",
                        "Azure Retail Pricing API"
                    ),
                }
                for item in service_prices.get(
                    "items",
                    []
                )
            ]
            total_monthly = (
                vm_price["monthly_cost"]
                + service_monthly
            )

            return {
                "provider": "Azure",
                "region": vm_price["region"],
                "currency": vm_price.get(
                    "currency",
                    "USD"
                ),
                "runtime_sku": vm_sku,
                "runtime_monthly": round(
                    vm_price["monthly_cost"],
                    2
                ),
                "services_monthly": round(
                    service_monthly,
                    2
                ),
                "service_breakdown": service_breakdown,
                "total_monthly": round(
                    total_monthly,
                    2
                ),
                "source": "Azure Retail Pricing API",
            }

        rows = await asyncio.gather(
            *[
                build_row(vm_price)
                for vm_price in vm_prices
            ]
        )

        return {
            "provider": "Azure",
            "currency": (
                rows[0]["currency"]
                if rows
                else "USD"
            ),
            "regions": sorted(
                rows,
                key=lambda item: item["total_monthly"]
            )
        }

    async def get_vm_prices_by_region(
        self,
        vm_sku: str
    ) -> list[dict]:

        """Get vm prices by region.
        
        Args:
            vm_sku: vm sku value.
        
        Returns:
            Get vm prices by region result.
        """
        filter_query = (
            f"serviceName eq 'Virtual Machines' "
            f"and armSkuName eq '{vm_sku}'"
        )

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            items = await self._get_all_retail_items(
                client,
                filter_query
            )

        regional_items: dict[str, dict] = {}

        for item in items:

            region = item.get(
                "armRegionName"
            )

            if not region:

                continue

            if not self._is_primary_consumption_item(
                item
            ):

                continue

            current = regional_items.get(
                region
            )

            if (
                current is None
                or item.get(
                    "retailPrice",
                    0
                )
                < current.get(
                    "retailPrice",
                    0
                )
            ):
                regional_items[region] = item

        if not regional_items:

            raise ValueError(
                f"No regional pricing found for {vm_sku}"
            )

        rows = []

        for region, item in regional_items.items():

            hourly_cost = item.get(
                "retailPrice",
                0
            )

            rows.append(
                {
                    "region": region,
                    "currency": item.get(
                        "currencyCode",
                        "USD"
                    ),
                    "hourly_cost": round(
                        hourly_cost,
                        6
                    ),
                    "monthly_cost": round(
                        hourly_cost
                        * 24
                        * 30,
                        2
                    ),
                }
            )

        return sorted(
            rows,
            key=lambda item: item["region"]
        )

    async def get_service_prices(
        self,
        region: str,
        services: list[dict]
    ) -> dict:

        """Get service prices.
        
        Args:
            region: region value.
            services: services value.
        
        Returns:
            Get service prices result.
        """
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

        """Find rule.
        
        Args:
            recommended: recommended value.
        
        Returns:
            Find rule result.
        """
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

        """Estimate service price.
        
        Args:
            region: region value.
            recommended: recommended value.
            rule: rule value.
        
        Returns:
            Estimate service price result.
        """
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

        """Get retail price item.
        
        Args:
            region: region value.
            rule: rule value.
        
        Returns:
            Get retail price item result.
        """
        filter_query = (
            f"serviceName eq '{rule['service_name']}' "
            f"and armRegionName eq '{region}'"
        )

        items = await self._get_retail_items(
            filter_query
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

    async def _get_all_retail_items(
        self,
        client: httpx.AsyncClient,
        filter_query: str
    ) -> list[dict]:

        """Get all retail items.
        
        Args:
            client: client value.
            filter_query: filter query value.
        
        Returns:
            Get all retail items result.
        """
        return await pricing_cache.get_or_set(
            "azure:retail:all_items",
            {
                "filter": filter_query
            },
            lambda: self._fetch_all_retail_items(
                client,
                filter_query
            )
        )

    async def _fetch_all_retail_items(
        self,
        client: httpx.AsyncClient,
        filter_query: str
    ) -> list[dict]:

        """Fetch all retail items.
        
        Args:
            client: client value.
            filter_query: filter query value.
        
        Returns:
            Fetch all retail items result.
        """
        items: list[dict] = []
        next_url = self.BASE_URL
        params = {
            "$filter": filter_query
        }

        while next_url:

            response = await client.get(
                next_url,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            items.extend(
                data.get(
                    "Items",
                    []
                )
            )
            next_url = data.get(
                "NextPageLink"
            )
            params = None

        return items

    async def _get_retail_items(
        self,
        filter_query: str
    ) -> list[dict]:

        """Get retail items.
        
        Args:
            filter_query: filter query value.
        
        Returns:
            Get retail items result.
        """
        return await pricing_cache.get_or_set(
            "azure:retail:first_page_items",
            {
                "filter": filter_query
            },
            lambda: self._fetch_retail_items(
                filter_query
            )
        )

    async def _fetch_retail_items(
        self,
        filter_query: str
    ) -> list[dict]:

        """Fetch retail items.
        
        Args:
            filter_query: filter query value.
        
        Returns:
            Fetch retail items result.
        """
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

        return data.get(
            "Items",
            []
        )

    def _is_primary_consumption_item(
        self,
        item: dict
    ) -> bool:

        """Is primary consumption item.
        
        Args:
            item: item value.
        
        Returns:
            Is primary consumption item result.
        """
        return (
            item.get("type") == "Consumption"
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
            and (
                "Reservation"
                not in item.get(
                    "meterName",
                    ""
                )
            )
        )

    def _item_contains(
        self,
        item: dict,
        term: str
    ) -> bool:

        """Item contains.
        
        Args:
            item: item value.
            term: term value.
        
        Returns:
            Item contains result.
        """
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
