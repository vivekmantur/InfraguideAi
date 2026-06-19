import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .analyzer import analyze_local_repository, analyze_repository
from .models import AssessmentRequest, BlueprintRequest, FolderAssessmentRequest, MigrationRequirements
from .recommendation import build_assessment, render_blueprint
from .services.mcp_client import CloudMcpClient

app = FastAPI(title="InfraGuide AI API", version="0.1.0")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://62.72.30.227:5174",
]


def _cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ORIGINS", "")
    origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    return origins or DEFAULT_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/assessments")
async def create_assessment(
    request: AssessmentRequest
):
    print(
        f"Received assessment request "
        f"for repository: "
        f"{request.repository_url}"
    )

    analysis, warnings = analyze_repository(
        str(request.repository_url),
        request.requirements,
        request.github_token
    )

    return await build_assessment(
        request,
        analysis,
        warnings
    )
@app.post("/assessments/upload")
async def create_uploaded_assessment(
    files: list[UploadFile] = File(...),
    requirements: str = Form(...),
    project_name: str = Form("Uploaded folder"),
):
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one project file.")

    try:
        parsed_requirements = MigrationRequirements.model_validate_json(requirements)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid migration requirements: {exc}") from exc

    tmp_dir = Path(tempfile.mkdtemp(prefix="infraguide-upload-"))
    total_bytes = 0
    saved_files = 0

    try:
        for upload in files:
            relative_path = _safe_upload_path(upload.filename or "uploaded-file")
            if relative_path is None:
                continue

            destination = tmp_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)

            content = await upload.read()
            total_bytes += len(content)
            if total_bytes > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=400, detail="Uploaded folder is too large for this MVP scan.")
            destination.write_bytes(content)
            saved_files += 1

        if saved_files == 0:
            raise HTTPException(status_code=400, detail="No analyzable files were found after ignoring dependency and build folders.")

        analysis, warnings = analyze_local_repository(
            tmp_dir,
            f"Uploaded folder: {project_name}",
            parsed_requirements
        )
        request = FolderAssessmentRequest(project_name=project_name, requirements=parsed_requirements)
        return await build_assessment(request, analysis, warnings)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/assessments/blueprint", response_class=PlainTextResponse)
def export_blueprint(request: BlueprintRequest):
    return render_blueprint(request.assessment)


@app.post("/pricing/regions")
async def regional_pricing(payload: dict):
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


@app.get("/cloud-intelligence/health")
async def cloud_intelligence_health():
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.health_check_cloud_intelligence()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Cloud intelligence health check failed: {exc}") from exc


@app.post("/cloud-intelligence/service-availability")
async def service_availability(payload: dict):
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.check_service_availability(
            payload["provider"],
            payload["region"],
            payload.get("services", [])
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Service availability check failed: {exc}") from exc


@app.post("/cloud-intelligence/runtime-support")
async def runtime_support(payload: dict):
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.check_runtime_support(
            payload["provider"],
            payload["target_service"],
            payload.get("runtimes", []),
            payload.get("frameworks", [])
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Runtime support check failed: {exc}") from exc


@app.post("/cloud-intelligence/service-limits")
async def service_limits(payload: dict):
    mcp_client = CloudMcpClient()

    try:
        return await mcp_client.get_service_limits(
            payload["provider"],
            payload["service"]
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing required field: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Service limits lookup failed: {exc}") from exc


def _safe_upload_path(filename: str) -> Path | None:
    ignored_parts = {"", ".", "..", ".git", "node_modules", "vendor", "bin", "obj", "dist", "build", ".venv", "venv", "env", "__pycache__"}
    parts = list(PurePosixPath(filename.replace("\\", "/")).parts)
    if any(part in ignored_parts for part in parts):
        return None
    parts = [part for part in parts if not part.endswith(":") and not part.startswith("/")]
    if not parts:
        return None
    return Path(*parts)
