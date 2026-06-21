import json
from pathlib import Path
from typing import Any
from services.pricing_cache import pricing_cache, redis_async

CATALOG_DIR = Path(__file__).resolve().parents[2] / "catalogs"
CATALOG_FILES = {
    "AWS": "aws.json",
    "Azure": "azure.json",
    "GCP": "gcp.json",
}
CATALOGS = {}

def _load_catalogs() -> dict[str, dict[str, Any]]:
    """Load catalogs.
    
    Returns:
        Load catalogs result.
    """
    catalogs: dict[str, dict[str, Any]] = {}

    for provider, filename in CATALOG_FILES.items():
        path = CATALOG_DIR / filename
        with path.open(encoding="utf-8") as catalog_file:
            data = json.load(catalog_file)

        catalogs[provider] = {
            "provider": provider,
            "source": data.get("source", "local_catalog"),
            "version": data.get("version", "unknown"),
            "regions": set(data.get("regions", [])),
            "service_aliases": {
                key.lower(): value
                for key, value in data.get("service_aliases", {}).items()
            },
            "service_limits": data.get("service_limits", {}),
            "runtime_support": {
                key: set(value)
                for key, value in data.get("runtime_support", {}).items()
            },
        }

    return catalogs

def _catalogs() -> dict[str, dict[str, Any]]:
    """Catalogs.
    
    Returns:
        Catalogs result.
    """
    global CATALOGS

    if not CATALOGS:
        CATALOGS = _load_catalogs()

    return CATALOGS

def register_cloud_intelligence_tools(mcp):
    """Register cloud intelligence MCP tools on the server.

    Args:
        mcp: MCP server instance that receives tool registrations.

    Returns:
        None.
    """

    @mcp.tool()
    async def health_check_cloud_intelligence() -> dict:
        """Health check cloud intelligence.
        
        Returns:
            Health check cloud intelligence result.
        """
        redis_status = "disabled"
        redis_error = None
        catalogs = _catalogs()

        if redis_async is None:
            redis_status = "redis package unavailable"
        elif not pricing_cache.enabled:
            redis_status = "disabled by configuration"
        else:
            try:
                client = await pricing_cache._get_client()
                await client.ping()
                redis_status = "ok"
            except Exception as ex:
                redis_status = "unavailable"
                redis_error = str(ex)

        return {
            "status": "ok" if redis_status in {"ok", "disabled by configuration"} else "degraded",
            "mcp": "ok",
            "catalogs": [
                {
                    "provider": provider,
                    "source": catalog["source"],
                    "version": catalog["version"],
                    "regions": len(catalog["regions"]),
                    "service_aliases": len(catalog["service_aliases"]),
                }
                for provider, catalog in catalogs.items()
            ],
            "redis_cache": {
                "status": redis_status,
                "url": pricing_cache.redis_url,
                "ttl_seconds": pricing_cache.ttl_seconds,
                "enabled": pricing_cache.enabled,
                "error": redis_error,
            },
            "tools": [
                "get_azure_vm_pricing",
                "get_gcp_compute_pricing",
                "get_azure_regional_pricing",
                "get_gcp_regional_pricing",
                "get_aws_regional_pricing",
                "check_service_availability",
                "check_runtime_support",
                "get_service_limits",
            ],
        }

    @mcp.tool()
    async def check_service_availability(
        provider: str,
        region: str,
        services: list,
    ) -> dict:
        """Check service availability for a cloud provider and region.
        
        Args:
            provider: provider value.
            region: region value.
            services: services value.
        
        Returns:
            Check service availability result.
        """
        normalized_provider = _provider_name(provider)
        catalogs = _catalogs()
        catalog = catalogs.get(normalized_provider)

        if not catalog:
            return {
                "provider": provider,
                "region": region,
                "available": [],
                "unavailable": services,
                "notes": [f"Unsupported provider: {provider}"],
            }

        region_supported = region in catalog["regions"]
        available = []
        unavailable = []
        notes = []

        for service in services:
            service_name = _service_name(service)
            category = _service_category(normalized_provider, service_name)
            row = {
                "component": service.get("component"),
                "service": service_name,
                "category": category,
            }

            if region_supported and category != "unknown":
                available.append(row)
            else:
                unavailable.append(row)

        if not region_supported:
            notes.append(f"{region} is not in the supported {normalized_provider} region list.")
        if unavailable and region_supported:
            notes.append("Some services are not recognized by the deterministic MCP service catalog.")

        return {
            "provider": normalized_provider,
            "region": region,
            "catalog_source": catalog["source"],
            "catalog_version": catalog["version"],
            "region_supported": region_supported,
            "available": available,
            "unavailable": unavailable,
            "notes": notes,
        }

    @mcp.tool()
    async def check_runtime_support(
        provider: str,
        target_service: str,
        runtimes: list,
        frameworks: list = None,
    ) -> dict:
        """Check runtime support for a provider service.
        
        Args:
            provider: provider value.
            target_service: target service value.
            runtimes: runtimes value.
            frameworks: frameworks value.
        
        Returns:
            Check runtime support result.
        """
        normalized_provider = _provider_name(provider)
        catalog = _catalogs().get(normalized_provider, {})
        supported = catalog.get("runtime_support", {}).get(target_service, set())
        normalized_runtimes = [_runtime_name(item) for item in runtimes]
        supported_runtimes = [item for item in normalized_runtimes if item in supported]
        unsupported_runtimes = [item for item in normalized_runtimes if item not in supported]
        notes = []

        if not supported:
            notes.append(f"No runtime support catalog entry found for {target_service} on {normalized_provider}.")
        if frameworks:
            notes.append("Framework compatibility should be validated with dependency and build settings.")

        return {
            "provider": normalized_provider,
            "target_service": target_service,
            "catalog_source": catalog.get("source"),
            "catalog_version": catalog.get("version"),
            "supported": len(unsupported_runtimes) == 0 and bool(normalized_runtimes) and bool(supported),
            "supported_runtimes": supported_runtimes,
            "unsupported_runtimes": unsupported_runtimes,
            "catalog_supported_runtimes": sorted(supported),
            "notes": notes,
        }

    @mcp.tool()
    async def get_service_limits(
        provider: str,
        service: str,
    ) -> dict:
        """Return service limit metadata for a provider service.
        
        Args:
            provider: provider value.
            service: service value.
        
        Returns:
            Get service limits result.
        """
        normalized_provider = _provider_name(provider)
        category = _service_category(normalized_provider, service)
        catalog = _catalogs().get(normalized_provider, {})
        limits = catalog.get("service_limits", {}).get(category, [])

        return {
            "provider": normalized_provider,
            "service": service,
            "catalog_source": catalog.get("source"),
            "catalog_version": catalog.get("version"),
            "category": category,
            "limits": limits,
            "notes": []
            if limits
            else ["No deterministic service limit entry found for this service."],
        }

def _provider_name(provider: str) -> str:
    """Provider name.
    
    Args:
        provider: provider value.
    
    Returns:
        Provider name result.
    """
    value = provider.strip().lower()
    if value == "aws":
        return "AWS"
    if value == "azure":
        return "Azure"
    if value == "gcp":
        return "GCP"
    return provider

def _service_name(service: dict) -> str:
    """Service name.
    
    Args:
        service: service value.
    
    Returns:
        Service name result.
    """
    return str(
        service.get("recommended")
        or service.get("service")
        or service.get("name")
        or service.get("component")
        or ""
    )

def _service_category(provider: str, service: str) -> str:
    """Service category.
    
    Args:
        provider: provider value.
        service: service value.
    
    Returns:
        Service category result.
    """
    catalog = _catalogs().get(provider, {})
    aliases = catalog.get("service_aliases", {})
    lowered = service.strip().lower()
    if lowered in aliases:
        return aliases[lowered]

    for key, category in aliases.items():
        if key in lowered or lowered in key:
            return category

    return "unknown"

def _runtime_name(runtime: str) -> str:
    """Runtime name.
    
    Args:
        runtime: runtime value.
    
    Returns:
        Runtime name result.
    """
    value = runtime.strip().lower()
    if value in {"node.js", "nodejs", "javascript", "typescript"}:
        return "node"
    if value in {"c#", "dotnet", "asp.net core", "asp.net"}:
        return ".net"
    if value.startswith("python"):
        return "python"
    if value.startswith("java"):
        return "java"
    if value.startswith("go"):
        return "go"
    return value
