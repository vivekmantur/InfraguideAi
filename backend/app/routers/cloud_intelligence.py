from fastapi import APIRouter, HTTPException

from ..services.mcp_client import CloudMcpClient

router = APIRouter(tags=["cloud-intelligence"])

@router.post("/pricing/regions")
async def regional_pricing(payload: dict):
    """Return regional pricing estimates for the selected cloud provider."""
    provider = payload.get("provider")
    cpu = int(payload.get("cpu", 2))
    memory = int(payload.get("memory", 4))
    limit = int(payload.get("limit", 10))
    region = payload.get("region")
    services = payload.get("services", [])
    mcp_client = CloudMcpClient()

    try:
        if provider == "GCP":
            return await mcp_client.get_gcp_regional_pricing(cpu, memory, services, limit, region)
        if provider == "Azure":
            return await mcp_client.get_azure_regional_pricing(cpu, memory, services, limit, region)
        if provider == "AWS":
            return await mcp_client.get_aws_regional_pricing(cpu, memory, services, limit, region)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Regional pricing failed: {exc}") from exc

    raise HTTPException(status_code=400, detail="Regional pricing is available for AWS, Azure, and GCP.")

@router.get("/cloud-intelligence/health")
async def cloud_intelligence_health():
    """Proxy a health check to the cloud intelligence bridge service."""
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.health_check_cloud_intelligence()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cloud intelligence health check failed: {exc}") from exc

@router.post("/cloud-intelligence/service-availability")
async def service_availability(payload: dict):
    """Validate whether recommended services are available in a region."""
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.check_service_availability(
            payload["provider"],
            payload["region"],
            payload.get("services", []),
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Service availability check failed: {exc}") from exc

@router.post("/cloud-intelligence/runtime-support")
async def runtime_support(payload: dict):
    """Check runtime and framework support for a target cloud service."""
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.check_runtime_support(
            payload["provider"],
            payload["target_service"],
            payload.get("runtimes", []),
            payload.get("frameworks", []),
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Runtime support check failed: {exc}") from exc

@router.post("/cloud-intelligence/service-limits")
async def service_limits(payload: dict):
    """Return service limit metadata for a provider service."""
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.get_service_limits(
            payload["provider"],
            payload["service"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Service limits lookup failed: {exc}") from exc
