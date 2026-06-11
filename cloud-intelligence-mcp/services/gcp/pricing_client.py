import httpx

from services.gcp.sku_selector import (
    select_machine_type
)


class GcpPricingClient:

    BASE_URL = (
        "https://cloudbilling.googleapis.com/v2beta"
    )

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

                    print(
                        f"Service: "
                        f"{display_name}"
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