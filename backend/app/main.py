import shutil
import tempfile
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .analyzer import analyze_local_repository, analyze_repository
from .models import AssessmentRequest, BlueprintRequest, FolderAssessmentRequest, MigrationRequirements
from .recommendation import build_assessment, render_blueprint

app = FastAPI(title="InfraGuide AI API", version="0.1.0")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
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

        analysis, warnings =analysis, warnings = analyze_local_repository(
            tmp_dir,
            f"Uploaded folder: {project_name}",
            parsed_requirements
        )
        request = FolderAssessmentRequest(project_name=project_name, requirements=parsed_requirements)
        return build_assessment(request, analysis, warnings)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/assessments/blueprint", response_class=PlainTextResponse)
def export_blueprint(request: BlueprintRequest):
    return render_blueprint(request.assessment)


def _safe_upload_path(filename: str) -> Path | None:
    ignored_parts = {"", ".", "..", ".git", "node_modules", "vendor", "bin", "obj", "dist", "build", ".venv", "venv", "env", "__pycache__"}
    parts = list(PurePosixPath(filename.replace("\\", "/")).parts)
    if any(part in ignored_parts for part in parts):
        return None
    parts = [part for part in parts if not part.endswith(":") and not part.startswith("/")]
    if not parts:
        return None
    return Path(*parts)
