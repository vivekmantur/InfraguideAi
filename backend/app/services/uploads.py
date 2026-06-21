import io
import zipfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
PROJECT_SOURCE_SUFFIXES = {
    ".cs",
    ".csproj",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sln",
    ".ts",
    ".tsx",
    ".vue",
}
PROJECT_SOURCE_FILES = {
    "angular.json",
    "app.py",
    "compose.yaml",
    "docker-compose.yml",
    "dockerfile",
    "go.mod",
    "host.json",
    "main.py",
    "manage.py",
    "next.config.js",
    "next.config.ts",
    "package.json",
    "pom.xml",
    "pyproject.toml",
    "requirements.txt",
    "settings.py",
    "vite.config.js",
    "vite.config.ts",
}

def safe_upload_path(filename: str) -> Path | None:
    """Normalize an uploaded path and reject dependency, build, or unsafe paths."""
    ignored_parts = {"", ".", "..", ".git", "node_modules", "vendor", "bin", "obj", "dist", "build", ".venv", "venv", "env", "__pycache__"}
    parts = list(PurePosixPath(filename.replace("\\", "/")).parts)
    if any(part in ignored_parts for part in parts):
        return None
    parts = [part for part in parts if not part.endswith(":") and not part.startswith("/")]
    if not parts:
        return None
    return Path(*parts)

def extract_project_zip(content: bytes, destination_root: Path) -> tuple[int, int]:
    """Extract analyzable ZIP entries into a temporary project directory."""
    total_uncompressed_bytes = 0
    saved_files = 0
    project_files = 0

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue

                relative_path = safe_upload_path(entry.filename)
                if relative_path is None:
                    continue

                total_uncompressed_bytes += entry.file_size
                if total_uncompressed_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=400, detail="Uploaded project ZIP is too large after extraction.")

                destination = destination_root / relative_path
                resolved_destination = destination.resolve()
                resolved_root = destination_root.resolve()
                if resolved_destination != resolved_root and resolved_root not in resolved_destination.parents:
                    continue

                destination.parent.mkdir(parents=True, exist_ok=True)
                extracted_content = archive.read(entry)
                if len(extracted_content) > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=400, detail="Uploaded project ZIP contains a file that is too large.")
                destination.write_bytes(extracted_content)
                saved_files += 1
                if is_project_source_path(relative_path):
                    project_files += 1
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive.") from exc

    return saved_files, project_files

def is_project_source_path(path: Path) -> bool:
    """Return whether a path looks like application source or project metadata."""
    name = path.name.lower()
    suffix = path.suffix.lower()
    return name in PROJECT_SOURCE_FILES or suffix in PROJECT_SOURCE_SUFFIXES
