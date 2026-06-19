from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3


AWS_PRICING_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "ca-central-1",
    "sa-east-1",
    "eu-west-1",
    "eu-west-2",
    "eu-central-1",
    "eu-north-1",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
]

AWS_REGION_LOCATIONS = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (Sao Paulo)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-north-1": "EU (Stockholm)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
}

HOURS_PER_MONTH = 730
PROJECT_AWS_DIR = Path(__file__).resolve().parents[3] / ".aws"


@dataclass(frozen=True)
class FargateRates:
    vcpu_hourly: float
    memory_gb_hourly: float


class AwsPricingClient:
    def __init__(self) -> None:
        self.client = self._session().client("pricing", region_name="us-east-1")
        self._fargate_cache: dict[str, FargateRates] = {}

    def _session(self) -> boto3.Session:
        credentials_file = PROJECT_AWS_DIR / "credentials"
        config_file = PROJECT_AWS_DIR / "config"

        if credentials_file.exists():
            os.environ.setdefault("AWS_SHARED_CREDENTIALS_FILE", str(credentials_file))
            os.environ.setdefault("AWS_CONFIG_FILE", str(config_file))
            return boto3.Session(profile_name=os.getenv("AWS_PROFILE", "infraguide"))

        return boto3.Session()

    def regional_pricing(
        self,
        cpu: int,
        memory: int,
        services: list[dict[str, Any]],
        limit: int = 10,
        region: str | None = None,
    ) -> dict[str, Any]:
        regions = [region] if region else AWS_PRICING_REGIONS
        rows = [
            self._region_price(
                region_code,
                cpu,
                memory,
                services,
            )
            for region_code in regions
            if region_code
        ]
        rows = sorted(rows, key=lambda item: item["total_monthly"])
        if limit and not region:
            rows = rows[:limit]

        return {
            "provider": "AWS",
            "currency": "USD",
            "regions": rows,
            "source": "AWS Price List API",
        }

    def _region_price(
        self,
        region: str,
        cpu: int,
        memory: int,
        services: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rates = self._fargate_rates(region)
        runtime_monthly = round(
            ((cpu * rates.vcpu_hourly) + (memory * rates.memory_gb_hourly)) * HOURS_PER_MONTH,
            2,
        )
        service_breakdown = self._service_breakdown(region, services)
        services_monthly = round(
            sum(item["monthly_cost"] for item in service_breakdown),
            2,
        )

        return {
            "provider": "AWS",
            "region": region,
            "currency": "USD",
            "runtime_sku": f"AWS Fargate ({cpu} vCPU, {memory} GB)",
            "runtime_monthly": runtime_monthly,
            "services_monthly": services_monthly,
            "service_breakdown": service_breakdown,
            "total_monthly": round(runtime_monthly + services_monthly, 2),
            "source": "AWS Price List API",
        }

    def _fargate_rates(self, region: str) -> FargateRates:
        if region in self._fargate_cache:
            return self._fargate_cache[region]

        location = AWS_REGION_LOCATIONS[region]
        products = self._get_products(
            "AmazonECS",
            [
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            ],
        )
        vcpu_hourly = self._find_price(
            products,
            lambda product: "Fargate-vCPU-Hours" in product.get("product", {}).get("attributes", {}).get("usagetype", ""),
        )
        memory_hourly = self._find_price(
            products,
            lambda product: "Fargate-GB-Hours" in product.get("product", {}).get("attributes", {}).get("usagetype", ""),
        )

        rates = FargateRates(
            vcpu_hourly=vcpu_hourly,
            memory_gb_hourly=memory_hourly,
        )
        self._fargate_cache[region] = rates
        return rates

    def _service_breakdown(
        self,
        region: str,
        services: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        breakdown: list[dict[str, Any]] = []

        for service in services:
            component = str(service.get("component", "Service"))
            recommended = str(service.get("recommended", "Managed service"))
            if component == "Application Runtime":
                continue

            monthly_cost = self._service_monthly_estimate(component, recommended, region)
            if monthly_cost <= 0:
                continue

            breakdown.append(
                {
                    "component": component,
                    "recommended": recommended,
                    "currency": "USD",
                    "monthly_cost": monthly_cost,
                    "source": "AWS Price List API/service assumption",
                }
            )

        return breakdown

    def _service_monthly_estimate(
        self,
        component: str,
        recommended: str,
        region: str,
    ) -> float:
        normalized = f"{component} {recommended}".lower()

        if "rds" in normalized or "database" in normalized:
            return self._rds_monthly(region)
        if "s3" in normalized or "storage" in normalized:
            return self._s3_monthly(region)
        if "secrets" in normalized:
            return 0.40
        if "cloudwatch" in normalized or "monitor" in normalized:
            return 2.50
        if "sqs" in normalized or "queue" in normalized:
            return 0.40
        if "kinesis" in normalized or "stream" in normalized:
            return 11.00
        if "glue" in normalized or "data integration" in normalized:
            return 22.00
        if "api gateway" in normalized:
            return 3.50
        if "cloudfront" in normalized or "waf" in normalized:
            return 8.00
        if "ecr" in normalized or "registry" in normalized:
            return 1.00

        return 0.0

    def _rds_monthly(self, region: str) -> float:
        location = AWS_REGION_LOCATIONS[region]
        products = self._get_products(
            "AmazonRDS",
            [
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "db.t4g.medium"},
                {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "PostgreSQL"},
                {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Single-AZ"},
            ],
        )
        hourly = self._find_price(
            products,
            lambda product: "InstanceUsage" in product.get("product", {}).get("attributes", {}).get("usagetype", ""),
            default=0.065,
        )
        return round(hourly * HOURS_PER_MONTH, 2)

    def _s3_monthly(self, region: str) -> float:
        location = AWS_REGION_LOCATIONS[region]
        products = self._get_products(
            "AmazonS3",
            [
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "storageClass", "Value": "General Purpose"},
            ],
        )
        gb_month = self._find_price(
            products,
            lambda product: "TimedStorage-ByteHrs" in product.get("product", {}).get("attributes", {}).get("usagetype", ""),
            default=0.023,
        )
        return round(gb_month * 50, 2)

    def _get_products(
        self,
        service_code: str,
        filters: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        paginator = self.client.get_paginator("get_products")

        for page in paginator.paginate(
            ServiceCode=service_code,
            Filters=filters,
            PaginationConfig={"MaxItems": 100},
        ):
            products.extend(json.loads(item) for item in page.get("PriceList", []))

        return products

    def _find_price(
        self,
        products: list[dict[str, Any]],
        predicate,
        default: float | None = None,
    ) -> float:
        for product in products:
            if not predicate(product):
                continue

            price = self._on_demand_price(product)
            if price is not None:
                return price

        if default is not None:
            return default

        raise ValueError("AWS Pricing API did not return a matching on-demand price.")

    def _on_demand_price(self, product: dict[str, Any]) -> float | None:
        terms = product.get("terms", {}).get("OnDemand", {})
        for term in terms.values():
            for dimension in term.get("priceDimensions", {}).values():
                price = dimension.get("pricePerUnit", {}).get("USD")
                if price is not None:
                    return float(price)
        return None
