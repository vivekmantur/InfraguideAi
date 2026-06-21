import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from ..analyzer import analyze_local_repository, analyze_repository
from ..models import AssessmentRequest, BlueprintRequest, FolderAssessmentRequest, MigrationRequirements
from ..services.assessment_builder import build_assessment, render_blueprint
from ..services.uploads import MAX_UPLOAD_BYTES, extract_project_zip, safe_upload_path

router = APIRouter(tags=["assessments"])


@router.post("/assessments")
async def create_assessment(request: AssessmentRequest):
    """Analyze a GitHub repository and build a migration assessment.

    Args:
        request: Assessment request containing repository URL and migration inputs.

    Returns:
        Complete migration assessment response.
    """
    analysis, warnings = analyze_repository(
        str(request.repository_url),
        request.requirements,
        request.github_token,
    )

    return await build_assessment(
        request,
        analysis,
        warnings,
    )


@router.post("/assessments/upload")
async def create_uploaded_assessment(
    files: list[UploadFile] = File(...),
    requirements: str = Form(...),
    project_name: str = Form("Uploaded folder"),
):
    """Analyze uploaded project files and return a migration assessment.

    Args:
        files: Uploaded project files from the browser.
        requirements: JSON migration requirements submitted with the upload.
        project_name: Display name for the uploaded project.

    Returns:
        Complete migration assessment response.
    """
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
            relative_path = safe_upload_path(upload.filename or "uploaded-file")
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
            parsed_requirements,
        )
        request = FolderAssessmentRequest(project_name=project_name, requirements=parsed_requirements)
        return await build_assessment(request, analysis, warnings)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/assessments/upload-zip")
async def create_zip_assessment(
    archive: UploadFile = File(...),
    requirements: str = Form(...),
    project_name: str = Form("Uploaded project"),
):
    """Extract an uploaded project ZIP and generate a migration assessment.

    Args:
        archive: Uploaded ZIP archive containing project source files.
        requirements: JSON migration requirements submitted with the upload.
        project_name: Display name for the uploaded project.

    Returns:
        Complete migration assessment response.
    """
    filename = archive.filename or "uploaded-project.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip file that contains your project source.")

    try:
        parsed_requirements = MigrationRequirements.model_validate_json(requirements)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid migration requirements: {exc}") from exc

    content = await archive.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded ZIP is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded project ZIP is too large for this MVP scan.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="infraguide-zip-"))

    try:
        saved_files, project_files = extract_project_zip(content, tmp_dir)
        if saved_files == 0:
            raise HTTPException(status_code=400, detail="No analyzable files were found after ignoring dependency and build folders.")
        if project_files == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Uploaded ZIP does not look like a project source archive. Upload a ZIP that includes source code "
                    "or project files such as package.json, requirements.txt, pom.xml, .py, .js, .ts, .java, or Dockerfile."
                ),
            )

        analysis, warnings = analyze_local_repository(
            tmp_dir,
            f"Uploaded ZIP: {project_name}",
            parsed_requirements,
        )
        request = FolderAssessmentRequest(project_name=project_name, requirements=parsed_requirements)
        return await build_assessment(request, analysis, warnings)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/assessments/blueprint", response_class=PlainTextResponse)
def export_blueprint(request: BlueprintRequest):
    """Render an assessment as a downloadable Markdown blueprint.

    Args:
        request: Blueprint export request containing the assessment.

    Returns:
        Markdown blueprint text.
    """
    return render_blueprint(request.assessment)
