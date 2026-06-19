import asyncio

import httpx

from services.pricing_cache import pricing_cache
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
                "Cloud SQL",
                "CPU"
            ],
            "preferred_terms": [
                "Zonal",
                "vCPU"
            ],
            "excluded_terms": [
                "Network",
                "Extended support",
                "Read Replica",
                "FDC Trial",
                "Enterprise Plus",
                "Performance Optimized",
                "Enterprise N4",
                "+",
                "Storage",
                "RAM"
            ],
            "fallback_monthly": 95,
        },
        {
            "match": "Cloud Storage",
            "service_display_name": "Cloud Storage",
            "quantity": 50,
            "unit": "GB-month",
            "required_terms": [
                "Standard",
                "Storage"
            ],
            "preferred_terms": [
                "Regional"
            ],
            "excluded_terms": [
                "Autoclass",
                "Dual-region",
                "Multi-region",
                "Operation",
                "Early Delete",
                "Archive",
                "Coldline",
                "Nearline"
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
                "Ingested"
            ],
            "preferred_terms": [
                "Metrics"
            ],
            "excluded_terms": [
                "API Requests",
                "Uptime Checks"
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
        self._compute_service_id: str | None = None
        self._service_id_cache: dict[str, str] = {}
        self._service_skus_cache: dict[str, list[dict]] = {}
        self._sku_price_cache: dict[str, dict] = {}

    async def get_compute_service_id(self):

        if self._compute_service_id:

            return self._compute_service_id

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
                            self._set_compute_service_id(
                                service["name"]
                                .split("/")[-1]
                            )
                        )

                page_token = data.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        raise ValueError(
            "Compute Engine service not found"
        )

    def _set_compute_service_id(
        self,
        service_id: str
    ) -> str:

        self._compute_service_id = service_id
        return service_id

    async def get_sku_price(
        self,
        sku_id: str
    ) -> dict:

        if sku_id in self._sku_price_cache:

            return self._sku_price_cache[sku_id]

        url = (
            f"{self.BASE_URL}/skus/"
            f"{sku_id}/price"
        )

        data = await pricing_cache.get_or_set(
            "gcp:sku_price",
            {
                "sku_id": sku_id
            },
            lambda: self._fetch_sku_price(
                sku_id
            )
        )

        sku_prices = data.get(
            "skuPrices",
            []
        )

        if not sku_prices:
            raise ValueError(
                f"No pricing found "
                f"for SKU {sku_id}"
            )

        default_prices = [
            p for p in sku_prices
            if (
                p.get(
                    "consumptionModelDescription"
                ) == "Default"
                or not p.get(
                    "consumptionModelDescription"
                )
            )
        ] or sku_prices

        tier = None
        first_tier = None

        for sku_price in default_prices:

            tiers = (
                sku_price
                .get(
                    "rate",
                    {}
                )
                .get(
                    "tiers",
                    []
                )
            )

            if not tiers:
                continue

            if first_tier is None:
                first_tier = tiers[0]

            for candidate_tier in tiers:

                list_price = (
                    candidate_tier.get(
                        "listPrice",
                        {}
                    )
                )
                units = float(
                    list_price.get(
                        "units",
                        0
                    )
                )
                nanos = float(
                    list_price.get(
                        "nanos",
                        0
                    )
                )

                if units or nanos:
                    tier = candidate_tier
                    break

            if tier is not None:
                break

        if tier is None and first_tier is not None:
            tier = first_tier

        if tier is None:

            raise ValueError(
                f"No rate tiers found "
                f"for SKU {sku_id}"
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

        result = {
            "sku_id": sku_id,
            "currency": data.get(
                "currencyCode",
                "USD"
            ),
            "hourly_cost":
                hourly_cost
        }

        self._sku_price_cache[sku_id] = result
        return result

    async def _fetch_sku_price(
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
            return response.json()

    async def find_compute_skus(
        self,
        machine_family: str
    ):

        service_id = await self.get_compute_service_id()
        skus = await self._load_service_skus(service_id)
        core_sku = None
        ram_sku = None

        for sku in skus:

            kind = self._compute_sku_kind(
                sku,
                machine_family
            )

            if kind is None:

                continue

            if not self._sku_matches_region(
                sku,
                "us-central1"
            ):

                continue

            if kind == "core_sku" and core_sku is None:
                core_sku = sku["skuId"]

            if kind == "ram_sku" and ram_sku is None:
                ram_sku = sku["skuId"]

            if core_sku and ram_sku:
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
        services: list[dict],
        limit: int = 10,
        region: str | None = None
    ) -> dict:

        compute_prices = await self.get_compute_prices_by_region(
            cpu,
            memory,
            limit,
            region
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
        memory: int,
        limit: int | None = None,
        region: str | None = None
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

            for sku_region in self._sku_regions(
                sku
            ):

                if sku_region == "global":

                    continue

                by_region.setdefault(
                    sku_region,
                    {}
                )[kind] = sku["skuId"]

        semaphore = asyncio.Semaphore(12)

        async def build_compute_row(
            region: str,
            regional_skus: dict
        ) -> dict | None:

            if (
                "core_sku" not in regional_skus
                or "ram_sku" not in regional_skus
            ):

                return None

            try:

                async with semaphore:

                    core_price, ram_price = await asyncio.gather(
                        self.get_sku_price(
                            regional_skus["core_sku"]
                        ),
                        self.get_sku_price(
                            regional_skus["ram_sku"]
                        )
                    )

            except Exception:

                return None

            hourly_cost = (
                core_price["hourly_cost"]
                * cpu
            ) + (
                ram_price["hourly_cost"]
                * memory
            )

            return {
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

        if region:
            desired_regions = [region]
        else:
            desired_regions = self.COMMON_REGIONS[
                :limit or len(self.COMMON_REGIONS)
            ]

        selected_regions = [
            (
                region_name,
                by_region.get(
                    region_name,
                    {}
                )
            )
            for region_name in desired_regions
        ]

        selected_region_names = [
            item[0]
            for item in selected_regions
        ]

        computed_rows = await asyncio.gather(
            *[
                build_compute_row(
                    region,
                    regional_skus
                )
                for region, regional_skus in selected_regions
            ]
        )
        rows = [
            row
            for row in computed_rows
            if row is not None
        ]

        missing_regions = [
            region
            for region in selected_region_names
            if region not in {
                row["region"]
                for row in rows
            }
        ]

        if missing_regions:

            fallback = await self.get_compute_price(
                cpu,
                memory
            )

            rows.extend(
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
                for region in missing_regions
            )

        print(
            f"Loaded {len(rows)} regional GCP compute prices"
        )

        ordered_rows = sorted(
            rows,
            key=lambda item: (
                selected_region_names.index(item["region"])
                if item["region"] in selected_region_names
                else len(selected_region_names),
                item["region"]
            )
        )

        return ordered_rows[:limit] if limit else ordered_rows

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
            and not any(
                self._sku_contains(
                    sku,
                    term
                )
                for term in rule.get(
                    "excluded_terms",
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

        ranked = sorted(
            preferred
            if preferred
            else candidates,
            key=lambda sku: self._service_sku_rank(
                sku,
                region
            )
        )

        return (
            ranked[0]
        )

    async def _find_service_id(
        self,
        display_name: str
    ) -> str:

        cache_key = display_name.upper()

        if cache_key in self._service_id_cache:

            return self._service_id_cache[cache_key]

        partial_match = None

        async for service in self._iter_services():

            service_display_name = service.get(
                "displayName",
                ""
            )

            if display_name.upper() == service_display_name.upper():

                service_id = (
                    service["name"]
                    .split("/")[-1]
                )
                self._service_id_cache[cache_key] = service_id
                return service_id

            if (
                partial_match is None
                and display_name.upper()
                in service_display_name.upper()
            ):

                partial_match = (
                    service["name"]
                    .split("/")[-1]
                )

        if partial_match:

            self._service_id_cache[cache_key] = partial_match
            return partial_match

        raise ValueError(
            f"{display_name} service not found"
        )

    async def _iter_services(
        self
    ):

        for service in await self._load_services():
            yield service

    async def _load_services(
        self
    ) -> list[dict]:

        return await pricing_cache.get_or_set(
            "gcp:services",
            {
                "page_size": 1000
            },
            self._fetch_services
        )

    async def _fetch_services(
        self
    ) -> list[dict]:

        url = (
            f"{self.BASE_URL}/services"
        )
        page_token = None
        services: list[dict] = []

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

                services.extend(
                    data.get(
                        "services",
                        []
                    )
                )

                page_token = data.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        return services

    async def _load_service_skus(
        self,
        service_id: str
    ) -> list[dict]:

        if service_id in self._service_skus_cache:

            return self._service_skus_cache[service_id]

        skus = await pricing_cache.get_or_set(
            "gcp:service_skus",
            {
                "service_id": service_id
            },
            lambda: self._fetch_service_skus(
                service_id
            )
        )

        self._service_skus_cache[service_id] = skus
        return skus

    async def _fetch_service_skus(
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

    def _service_sku_rank(
        self,
        sku: dict,
        region: str
    ) -> tuple[int, str]:

        regions = self._sku_regions(
            sku
        )
        display_name = sku.get(
            "displayName",
            ""
        )
        lower_name = display_name.lower()

        rank = 0

        if regions == [
            region
        ]:
            rank -= 30

        if region in regions:
            rank -= 10

        if "global" in regions:
            rank += 20

        if "regional" in lower_name:
            rank -= 5

        if "multi-region" in lower_name:
            rank += 8

        if "dual-region" in lower_name:
            rank += 8

        return (
            rank,
            display_name
        )
