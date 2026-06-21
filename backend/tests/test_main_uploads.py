from __future__ import annotations
import io
import zipfile
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.services.uploads import extract_project_zip, safe_upload_path

client = TestClient(app)

def test_safe_upload_path_rejects_ignored_and_unsafe_parts():
    """Verify upload paths skip dependency/build folders and traversal entries."""
    assert safe_upload_path("project/src/app.py").as_posix() == "project/src/app.py"
    assert safe_upload_path("project/node_modules/package/index.js") is None
    assert safe_upload_path("../secrets.env") is None
    assert safe_upload_path("project/.git/config") is None

def test_extract_project_zip_skips_ignored_entries(tmp_path):
    """Verify ZIP extraction ignores dependency files and saves source files."""
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("project/src/app.py", "print('ok')")
        archive.writestr("project/node_modules/lib.js", "ignored")

    saved_count, project_file_count = extract_project_zip(archive_bytes.getvalue(), tmp_path)

    assert saved_count == 1
    assert project_file_count == 1
    assert (tmp_path / "project" / "src" / "app.py").exists()
    assert not (tmp_path / "project" / "node_modules" / "lib.js").exists()

def test_extract_project_zip_counts_manifest_as_project_source(tmp_path):
    """Verify project manifests count as source signals even without code files."""
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("project/package.json", '{"dependencies": {"react": "latest"}}')
        archive.writestr("project/README.md", "Project notes")

    saved_count, project_file_count = extract_project_zip(archive_bytes.getvalue(), tmp_path)

    assert saved_count == 2
    assert project_file_count == 1
    assert (tmp_path / "project" / "package.json").exists()

def test_extract_project_zip_returns_zero_project_files_for_document_archive(tmp_path):
    """Verify valid ZIPs without source signals can be rejected by the endpoint."""
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("notes/resume.txt", "not an application project")
        archive.writestr("notes/profile.md", "not enough to scan")

    saved_count, project_file_count = extract_project_zip(archive_bytes.getvalue(), tmp_path)

    assert saved_count == 2
    assert project_file_count == 0

def test_upload_zip_rejects_non_project_archive():
    """Verify the upload endpoint returns a clear error for non-project ZIP files."""
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("RESUME.txt", "not a project")

    response = client.post(
        "/assessments/upload-zip",
        data={
            "project_name": "RESUME",
            "requirements": (
                '{"cloud_provider":"AWS","migration_goal":"Cost Optimization",'
                '"expected_traffic":"Low","budget_preference":"Low Cost",'
                '"migration_timeline":"3 Months"}'
            ),
        },
        files={"archive": ("RESUME.zip", archive_bytes.getvalue(), "application/zip")},
    )

    assert response.status_code == 400
    assert "does not look like a project source archive" in response.json()["detail"]

def test_extract_project_zip_rejects_invalid_zip(tmp_path):
    """Verify invalid ZIP content raises a validation error."""
    with pytest.raises(HTTPException) as exc:
        extract_project_zip(b"not-a-zip", tmp_path)

    assert exc.value.status_code == 400
