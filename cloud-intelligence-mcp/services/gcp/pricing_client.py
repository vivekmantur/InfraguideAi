import asyncio

import httpx

from services.gcp.sku_selector import (
    select_machine_type
)


class GcpPricingClient:

    BASE_URL = (
        "https://cloudbilling.googleapis.com/v2beta"
    )

    SERVICE_RULES = [
        {
            "match": "Cloud SQL",
            "service_display_name": "Cloud SQL",
            "quantity": 730,
            "unit": "vCPU-hours/month",
            "required_terms": [
                "CPU"
            ],
            "fallback_monthly": 95,
        },
        {
            "match": "Cloud Storage",
            "service_display_name": "Cloud Storage",
            "quantity": 50,
            "unit": "GB-month",
            "required_terms": [
                "Storage"
            ],
            "preferred_terms": [
                "Standard"
            ],
            "fallback_monthly": 2,
        },
        {
            "match": "Secret Manager",
            "service_display_name": "Secret Manager",
            "quantity": 10,
            "unit": "10k operations/month",
            "required_terms": [
                "Access"
            ],
            "fallback_monthly": 1,
        },
        {
            "match": "Cloud Monitoring",
            "service_display_name": "Cloud Monitoring",
            "quantity": 5,
            "unit": "GB ingested/month",
            "required_terms": [
                "Monitoring"
            ],
            "preferred_terms": [
                "Data"
            ],
            "fallback_monthly": 15,
        },
    ]

    COMMON_REGIONS = [
        "us-central1",
        "us-east1",
        "us-east4",
        "us-west1",
        "us-west2",
        "northamerica-northeast1",
        "southamerica-east1",
        "europe-west1",
        "europe-west2",
        "europe-west3",
        "europe-west4",
        "europe-north1",
        "asia-south1",
        "asia-east1",
        "asia-east2",
        "asia-northeast1",
        "asia-southeast1",
        "australia-southeast1",
    ]

    def __init__(
        self,
        api_key: str
    ):
        self.api_key = api_key

    async def get_compute_service_id(self):

        url = (
            f"{self.BASE_URL}/services"
        )

        page_token = None

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            while True:

                params = {
                    "key": self.api_key,
                    "pageSize": 1000
                }

                if page_token:
                    params["pageToken"] = (
                        page_token
                    )

                response = await client.get(
                    url,
                    params=params
                )

                response.raise_for_status()

                data = response.json()

                services = data.get(
                    "services",
                    []
                )

                print(
                    f"Loaded "
                    f"{len(services)} services"
                )

                for service in services:

                    display_name = (
                        service.get(
                            "displayName",
                            ""
                        )
                    )

                    if (
                        "COMPUTE ENGINE"
                        in display_name.upper()
                    ):
                        print(
                            "Found Compute Engine:"
                        )
                        print(service)

                        return (
                            service["name"]
                            .split("/")[-1]
                        )

                page_token = data.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        raise ValueError(
            "Compute Engine service not found"
        )

    async def get_sku_price(
        self,
        sku_id: str
    ) -> dict:

        url = (
            f"{self.BASE_URL}/skus/"
            f"{sku_id}/price"
        )

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(
                url,
                params={
                    "key": self.api_key
                }
            )

            response.raise_for_status()

            data = response.json()

            sku_prices = data.get(
                "skuPrices",
                []
            )

            if not sku_prices:
                raise ValueError(
                    f"No pricing found "
                    f"for SKU {sku_id}"
                )

            default_price = next(
                (
                    p for p in sku_prices
                    if p.get(
                        "consumptionModelDescription"
                    ) == "Default"
                ),
                sku_prices[0]
            )

            tier = (
                default_price["rate"]
                ["tiers"][0]
            )

            list_price = (
                tier["listPrice"]
            )

            units = float(
                list_price.get(
                    "units",
                    0
                )
            )

            nanos = (
                float(
                    list_price.get(
                        "nanos",
                        0
                    )
                )
                / 1_000_000_000
            )

            hourly_cost = (
                units + nanos
            )

            return {
                "sku_id": sku_id,
                "currency": data.get(
                    "currencyCode",
                    "USD"
                ),
                "hourly_cost":
                    hourly_cost
            }

    async def find_compute_skus(
        self,
        machine_family: str
    ):

        service_id = (
            await self
            .get_compute_service_id()
        )

        url = (
            f"{self.BASE_URL}/skus"
        )

        core_sku = None
        ram_sku = None

        page_token = None

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            while True:

                params = {
                    "filter":
                        f'service="services/{service_id}"',
                    "key": self.api_key,
                    "pageSize": 5000
                }

                if page_token:
                    params["pageToken"] = (
                        page_token
                    )

                response = await client.get(
                    url,
                    params=params
                )

                response.raise_for_status()

                data = response.json()

                skus = data.get(
                    "skus",
                    []
                )

                print(
                    f"Loaded "
                    f"{len(skus)} SKUs"
                )

                for sku in skus:

                    display_name = (
                        sku.get(
                            "displayName",
                            ""
                        )
                        .upper()
                    )

                    if (
                        machine_family.upper()
                        in display_name
                    ):

                        if (
                            "CORE"
                            in display_name
                            and core_sku is None
                        ):
                            core_sku = (
                                sku["skuId"]
                            )

                            print(
                                f"Found CORE SKU: "
                                f"{core_sku}"
                            )

                        if (
                            "RAM"
                            in display_name
                            and ram_sku is None
                        ):
                            ram_sku = (
                                sku["skuId"]
                            )

                            print(
                                f"Found RAM SKU: "
                                f"{ram_sku}"
                            )

                    if (
                        core_sku
                        and ram_sku
                    ):
                        break

                if (
                    core_sku
                    and ram_sku
                ):
                    break

                page_token = data.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        if not core_sku:
            raise ValueError(
                f"Core SKU not found "
                f"for {machine_family}"
            )

        if not ram_sku:
            raise ValueError(
                f"RAM SKU not found "
                f"for {machine_family}"
            )

        return {
            "core_sku": core_sku,
            "ram_sku": ram_sku
        }

    async def get_compute_price(
        self,
        cpu: int,
        memory: int
    ):

        machine = (
            select_machine_type(
                cpu,
                memory
            )
        )

        print(
            "Selected machine:"
        )
        print(machine)

        skus = (
            await self
            .find_compute_skus(
                machine[
                    "machine_family"
                ]
            )
        )

        core_price = (
            await self
            .get_sku_price(
                skus["core_sku"]
            )
        )

        ram_price = (
            await self
            .get_sku_price(
                skus["ram_sku"]
            )
        )

        hourly_compute_cost = (
            core_price[
                "hourly_cost"
            ]
            * cpu
        )

        hourly_memory_cost = (
            ram_price[
                "hourly_cost"
            ]
            * memory
        )

        total_hourly_cost = (
            hourly_compute_cost
            + hourly_memory_cost
        )

        monthly_cost = (
            total_hourly_cost
            * 24
            * 30
        )

        return {
            "provider": "GCP",
            "machine_type":
                machine[
                    "machine_type"
                ],
            "machine_family":
                machine[
                    "machine_family"
                ],
            "cpu": cpu,
            "memory": memory,
            "currency":
                core_price[
                    "currency"
                ],
            "hourly_cost":
                round(
                    total_hourly_cost,
                    6
                ),
            "monthly_cost":
                round(
                    monthly_cost,
                    2
                ),
            "core_sku":
                skus[
                    "core_sku"
                ],
            "ram_sku":
                skus[
                    "ram_sku"
                ]
        }

    async def get_regional_prices(
        self,
        cpu: int,
        memory: int,
        services: list[dict]
    ) -> dict:

        compute_prices = await self.get_compute_prices_by_region(
            cpu,
            memory
        )
        semaphore = asyncio.Semaphore(8)

        async def build_row(
            compute_price: dict
        ) -> dict:

            async with semaphore:

                service_prices = await self.get_service_prices(
                    compute_price["region"],
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
                        "Google Cloud Billing API"
                    ),
                }
                for item in service_prices.get(
                    "items",
                    []
                )
            ]
            total_monthly = (
                compute_price["monthly_cost"]
                + service_monthly
            )

            return {
                "provider": "GCP",
                "region": compute_price["region"],
                "currency": compute_price.get(
                    "currency",
                    "USD"
                ),
                "runtime_sku": compute_price.get(
                    "machine_type",
                    ""
                ),
                "runtime_monthly": round(
                    compute_price["monthly_cost"],
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
                "source": "Google Cloud Billing API",
            }

        rows = await asyncio.gather(
            *[
                build_row(compute_price)
                for compute_price in compute_prices
            ]
        )

        return {
            "provider": "GCP",
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

    async def get_compute_prices_by_region(
        self,
        cpu: int,
        memory: int
    ) -> list[dict]:

        machine = select_machine_type(
            cpu,
            memory
        )
        service_id = await self.get_compute_service_id()
        skus = await self._load_service_skus(
            service_id
        )

        by_region: dict[str, dict] = {}

        for sku in skus:

            kind = self._compute_sku_kind(
                sku,
                machine["machine_family"]
            )

            if kind is None:

                continue

            for region in self._sku_regions(
                sku
            ):

                if region == "global":

                    continue

                by_region.setdefault(
                    region,
                    {}
                )[kind] = sku["skuId"]

        rows = []

        for region, regional_skus in by_region.items():

            if (
                "core_sku" not in regional_skus
                or "ram_sku" not in regional_skus
            ):

                continue

            try:

                core_price = await self.get_sku_price(
                    regional_skus["core_sku"]
                )
                ram_price = await self.get_sku_price(
                    regional_skus["ram_sku"]
                )

            except Exception:

                continue

            hourly_cost = (
                core_price["hourly_cost"]
                * cpu
            ) + (
                ram_price["hourly_cost"]
                * memory
            )

            rows.append(
                {
                    "region": region,
                    "currency": core_price.get(
                        "currency",
                        "USD"
                    ),
                    "machine_type": machine[
                        "machine_type"
                    ],
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
                    "core_sku": regional_skus[
                        "core_sku"
                    ],
                    "ram_sku": regional_skus[
                        "ram_sku"
                    ],
                }
            )

        if not rows:

            fallback = await self.get_compute_price(
                cpu,
                memory
            )

            return [
                {
                    "region": region,
                    "currency": fallback.get(
                        "currency",
                        "USD"
                    ),
                    "machine_type": fallback.get(
                        "machine_type",
                        machine["machine_type"]
                    ),
                    "hourly_cost": fallback.get(
                        "hourly_cost",
                        0
                    ),
                    "monthly_cost": fallback.get(
                        "monthly_cost",
                        0
                    ),
                    "core_sku": fallback.get(
                        "core_sku"
                    ),
                    "ram_sku": fallback.get(
                        "ram_sku"
                    ),
                }
                for region in self.COMMON_REGIONS
            ]

        print(
            f"Loaded {len(rows)} regional GCP compute prices"
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
            "provider": "GCP",
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

            sku = await self._find_service_sku(
                region,
                rule
            )
            price = await self.get_sku_price(
                sku["skuId"]
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
                    "baseline fallback because Google Cloud "
                    f"Billing lookup failed: {str(ex)}"
                ),
                "sku_id": None,
                "sku_name": recommended,
            }

        monthly_cost = (
            price["hourly_cost"]
            * rule["quantity"]
        )

        return {
            "currency": price.get(
                "currency",
                "USD"
            ),
            "monthly_cost": round(
                monthly_cost,
                2
            ),
            "quantity": rule["quantity"],
            "unit": rule["unit"],
            "source": "Google Cloud Billing API",
            "sku_id": sku.get(
                "skuId"
            ),
            "sku_name": sku.get(
                "displayName"
            ),
            "service_regions": self._sku_regions(
                sku
            )
        }

    async def _find_service_sku(
        self,
        region: str,
        rule: dict
    ) -> dict:

        service_id = await self._find_service_id(
            rule["service_display_name"]
        )

        skus = await self._load_service_skus(
            service_id
        )

        candidates = [
            sku
            for sku in skus
            if self._sku_matches_region(
                sku,
                region
            )
            and all(
                self._sku_contains(
                    sku,
                    term
                )
                for term in rule.get(
                    "required_terms",
                    []
                )
            )
        ]

        if not candidates:

            raise ValueError(
                f"No SKU matched "
                f"{rule['service_display_name']}"
            )

        preferred = [
            sku
            for sku in candidates
            if all(
                self._sku_contains(
                    sku,
                    term
                )
                for term in rule.get(
                    "preferred_terms",
                    []
                )
            )
        ]

        return (
            preferred[0]
            if preferred
            else candidates[0]
        )

    async def _find_service_id(
        self,
        display_name: str
    ) -> str:

        async for service in self._iter_services():

            service_display_name = service.get(
                "displayName",
                ""
            )

            if (
                display_name.upper()
                in service_display_name.upper()
            ):

                return (
                    service["name"]
                    .split("/")[-1]
                )

        raise ValueError(
            f"{display_name} service not found"
        )

    async def _iter_services(
        self
    ):

        url = (
            f"{self.BASE_URL}/services"
        )
        page_token = None

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            while True:

                params = {
                    "key": self.api_key,
                    "pageSize": 1000
                }

                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(
                    url,
                    params=params
                )
                response.raise_for_status()

                data = response.json()

                for service in data.get(
                    "services",
                    []
                ):
                    yield service

                page_token = data.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

    async def _load_service_skus(
        self,
        service_id: str
    ) -> list[dict]:

        url = (
            f"{self.BASE_URL}/skus"
        )
        page_token = None
        skus: list[dict] = []

        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            while True:

                params = {
                    "filter":
                        f'service="services/{service_id}"',
                    "key": self.api_key,
                    "pageSize": 5000
                }

                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(
                    url,
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                skus.extend(
                    data.get(
                        "skus",
                        []
                    )
                )

                page_token = data.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        return skus

    def _sku_matches_region(
        self,
        sku: dict,
        region: str
    ) -> bool:

        service_regions = self._sku_regions(
            sku
        )

        return (
            not service_regions
            or "global" in service_regions
            or region in service_regions
        )

    def _sku_regions(
        self,
        sku: dict
    ) -> list[str]:

        service_regions = sku.get(
            "serviceRegions",
            []
        )

        if service_regions:

            return service_regions

        geo_taxonomy = sku.get(
            "geoTaxonomy",
            {}
        )

        if isinstance(
            geo_taxonomy,
            dict
        ):

            regional_metadata = geo_taxonomy.get(
                "regionalMetadata",
                {}
            )

            if isinstance(
                regional_metadata,
                dict
            ):

                region = (
                    regional_metadata
                    .get(
                        "region",
                        {}
                    )
                    .get(
                        "region"
                    )
                )

                if region:

                    return [
                        region
                    ]

            multi_regional_metadata = geo_taxonomy.get(
                "multiRegionalMetadata",
                {}
            )

            if isinstance(
                multi_regional_metadata,
                dict
            ):

                regions = [
                    item.get(
                        "region"
                    )
                    for item in multi_regional_metadata.get(
                        "regions",
                        []
                    )
                    if item.get(
                        "region"
                    )
                ]

                if regions:

                    return regions

            regions = geo_taxonomy.get(
                "regions",
                []
            )

            if regions:

                return regions

            if (
                geo_taxonomy.get(
                    "type",
                    ""
                )
                .upper()
                == "GLOBAL"
            ):

                return [
                    "global"
                ]

        return []

    def _compute_sku_kind(
        self,
        sku: dict,
        machine_family: str
    ) -> str | None:

        display_name = (
            sku.get(
                "displayName",
                ""
            )
            .upper()
        )
        family = machine_family.upper()

        excluded_terms = [
            "SPOT",
            "PREEMPTIBLE",
            "CUSTOM",
            "SOLE TENANCY",
            "COMMITTED",
            "COMMITMENT",
            "PREMIUM",
            "OVERCOMMIT",
        ]

        if any(
            term in display_name
            for term in excluded_terms
        ):

            return None

        if (
            family == "N2"
            and "N2D" in display_name
        ):

            return None

        if (
            family == "E2"
            and "E2D" in display_name
        ):

            return None

        if f"{family} INSTANCE CORE" in display_name:

            return "core_sku"

        if (
            f"{family} INSTANCE RAM" in display_name
            or f"{family} INSTANCE MEMORY" in display_name
        ):

            return "ram_sku"

        return None

    def _sku_contains(
        self,
        sku: dict,
        term: str
    ) -> bool:

        haystack = " ".join(
            str(
                sku.get(
                    field,
                    ""
                )
            )
            for field in (
                "displayName",
                "description",
                "category",
                "geoTaxonomy"
            )
        )

        return term.lower() in haystack.lower()
