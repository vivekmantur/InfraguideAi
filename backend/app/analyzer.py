from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Iterable

from .ai import analyze_repository_evidence
from .models import RepositoryAnalysis

MAX_FILE_SCAN = 800
MAX_EVIDENCE_FILES = 80
MAX_FILE_CHARS = 6000
MAX_TOTAL_CHARS = 90000
WINDOWS_GIT = Path("C:/Program Files/Git/cmd/git.exe")

if WINDOWS_GIT.exists() and "GIT_PYTHON_GIT_EXECUTABLE" not in os.environ:
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = str(WINDOWS_GIT)

from git import Repo


def analyze_repository(repository_url: str) -> tuple[RepositoryAnalysis, list[str]]:
    warnings: list[str] = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="infraguide-"))

    try:
        Repo.clone_from(repository_url, tmp_dir, depth=1)
        files = list(_iter_repo_files(tmp_dir))
        detected_files = [str(path.relative_to(tmp_dir)).replace("\\", "/") for path in files]
        evidence = _collect_evidence(files, tmp_dir)
        analysis, llm_warnings = analyze_repository_evidence(repository_url, detected_files, evidence)
        warnings.extend(llm_warnings)
        return analysis, warnings
    except Exception as exc:
        warnings.append(f"Repository clone failed: {exc}")
        return _empty_analysis(), warnings
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _iter_repo_files(root: Path) -> Iterable[Path]:
    ignored_parts = {".git", "node_modules", "bin", "obj", "dist", "build", ".venv", "__pycache__"}
    count = 0

    for path in root.rglob("*"):
        if count >= MAX_FILE_SCAN:
            break
        if not path.is_file():
            continue
        if any(part in ignored_parts for part in path.parts):
            continue
        count += 1
        yield path


def _collect_evidence(files: list[Path], root: Path) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    total_chars = 0

    for path in sorted(files, key=_evidence_priority):
        if len(evidence) >= MAX_EVIDENCE_FILES or total_chars >= MAX_TOTAL_CHARS:
            break
        if not _looks_textual(path):
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        if not text.strip():
            continue

        snippet = _redact_sensitive_values(text[:MAX_FILE_CHARS])
        total_chars += len(snippet)
        evidence.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "content": snippet,
            }
        )

    return evidence


def _evidence_priority(path: Path) -> tuple[int, str]:
    name = path.name.lower()
    path_text = str(path).replace("\\", "/").lower()

    if name in {"readme.md", "package.json", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle"}:
        return (0, path_text)
    if name in {"host.json", "function.json", "local.settings.json", "dockerfile", "docker-compose.yml", "docker-compose.yaml"}:
        return (1, path_text)
    if ".github/workflows/" in path_text or name in {"azure-pipelines.yml", ".gitlab-ci.yml", "jenkinsfile"}:
        return (2, path_text)
    if path.suffix.lower() in {".py", ".cs", ".js", ".ts", ".tsx", ".java", ".go"}:
        return (3, path_text)
    if path.suffix.lower() in {".json", ".yaml", ".yml", ".tf", ".env", ".example", ".md"}:
        return (4, path_text)
    return (9, path_text)


def _looks_textual(path: Path) -> bool:
    if path.stat().st_size > 250_000:
        return False
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".7z", ".exe", ".dll"}:
        return False
    return True


def _redact_sensitive_values(text: str) -> str:
    redacted = text
    patterns = [
        r"(?i)(api[_-]?key|secret|password|pwd|token|client[_-]?secret|connection[_-]?string)\s*[:=]\s*['\"]?[^'\"\n]+",
        r"(?i)(authorization:\s*bearer\s+)[a-z0-9._\-]+",
        r"(?i)(defaultendpointsprotocol=.*?accountkey=)[^;\n]+",
    ]
    for pattern in patterns:
        redacted = re.sub(pattern, lambda match: f"{match.group(1)}=<redacted>", redacted)
    return redacted


def _empty_analysis() -> RepositoryAnalysis:
    return RepositoryAnalysis(
        languages=[],
        frameworks=[],
        runtimes=[],
        hosting_model="Unknown",
        deployment_model="Unknown",
        triggers=[],
        databases=[],
        package_managers=[],
        container_configs=[],
        infrastructure_configs=[],
        cicd_configs=[],
        external_dependencies=[],
        cloud_dependencies=[],
        dependency_graph=[],
        architecture_pattern="Unknown",
        application_type="Unknown",
        stateful_services=[],
        storage_dependencies=[],
        network_requirements=[],
        governance_findings=[],
        detected_files=[],
    )
