from __future__ import annotations
import os
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Iterable
from urllib.parse import quote, urlsplit, urlunsplit
import subprocess
import httpx

from .ai import analyze_repository_evidence
from .models import MigrationRequirements, RepositoryAnalysis

MAX_EVIDENCE_FILES = 20
MAX_FILE_CHARS = 1000
MAX_TOTAL_CHARS = 15000
WINDOWS_GIT = Path("C:/Program Files/Git/cmd/git.exe")
IGNORED_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "node_modules",
    "vendor",
    "bin",
    "obj",
    "dist",
    "build",
    ".next",
    "coverage",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".vs",
    ".nuget",
    "packages",
    "artifacts",
    "TestResults",
}
IGNORED_FILE_NAMES = {
    "tsconfig.tsbuildinfo",
}
NON_EVIDENCE_FILE_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pipfile.lock",
}

if WINDOWS_GIT.exists() and "GIT_PYTHON_GIT_EXECUTABLE" not in os.environ:
    os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = str(WINDOWS_GIT)

def analyze_repository(repository_url: str, migration_requirements,github_token: str | None = None) -> tuple[RepositoryAnalysis, list[str]]:
    """Clone a GitHub repository and analyze its source evidence.

    Args:
        repository_url: HTTPS repository URL to clone.
        migration_requirements: User-selected migration requirements used by LLM analysis.
        github_token: Optional GitHub access token for private repositories.

    Returns:
        Repository analysis and user-visible warnings produced during scanning.
    """
    warnings: list[str] = []
    temp_root = Path(__file__).resolve().parents[2] / ".tmp" / "repo-clones"
    temp_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(
    tempfile.mkdtemp(
        prefix="infraguide-",
        dir=temp_root
    )
)
    try:
        if (
            not (github_token or "").strip()
            and _github_repository_needs_token(repository_url)
        ):
            warnings.append(
                "Repository clone failed: private repository or repository not accessible without a GitHub access token."
            )
            return _empty_analysis(), warnings

        _clone_repository(
            _authenticated_github_url(
                repository_url,
                github_token
            ),
            tmp_dir
        )
        files = list(_iter_repo_files(tmp_dir))
        detected_files = [str(path.relative_to(tmp_dir)).replace("\\", "/") for path in files]
        evidence = _collect_evidence(files, tmp_dir)
        fallback = _infer_repository_analysis(detected_files, evidence)
        analysis, llm_warnings = analyze_repository_evidence(
            fallback,
            migration_requirements

        )
        warnings.extend(llm_warnings)
        return _merge_analysis(fallback, analysis), warnings
    except Exception as exc:
        warnings.append(f"Repository clone failed: {_safe_clone_error(str(exc), github_token)}")
        return _empty_analysis(), warnings
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def _non_interactive_git_env() -> dict[str, str]:
    """Build environment variables that prevent Git from prompting interactively.

    Args:
        None.

    Returns:
        Environment dictionary for non-interactive Git subprocess calls.
    """
    env = os.environ.copy()
    env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
        }
    )
    return env

def _clone_repository(
    repository_url: str,
    destination: Path
) -> None:
    """Clone a repository into the destination path using a shallow checkout.

    Args:
        repository_url: Repository URL, optionally already token-authenticated.
        destination: Directory where the repository should be cloned.

    Returns:
        None.

    Raises:
        RuntimeError: If git clone exits with a non-zero status.
    """
    git_executable = (
        str(WINDOWS_GIT)
        if WINDOWS_GIT.exists()
        else "git"
    )
    result = subprocess.run(
        [
            git_executable,
            "-c",
            "credential.helper=",
            "-c",
            "core.askPass=",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--filter=blob:none",
            repository_url,
            str(destination)
        ],
        capture_output=True,
        text=True,
        env=_non_interactive_git_env(),
        timeout=300
    )

    if result.returncode != 0:
        message = (
            result.stderr.strip()
            or result.stdout.strip()
            or "git clone failed"
        )
        raise RuntimeError(message)

def _github_repository_needs_token(repository_url: str) -> bool:
    """Return whether GitHub reports the repository is not publicly accessible.

    Args:
        repository_url: GitHub repository URL to probe.

    Returns:
        True when GitHub returns an authentication or not-found response; otherwise False.
    """
    split = urlsplit(repository_url)

    if split.scheme not in {"http", "https"} or split.hostname != "github.com":
        return False

    parts = [
        part for part in split.path.strip("/").split("/")
        if part
    ]

    if len(parts) < 2:
        return False

    owner = parts[0]
    repo = parts[1].removesuffix(".git")

    try:
        response = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            timeout=8,
            headers={
                "Accept": "application/vnd.github+json"
            }
        )

    except Exception:
        return False

    return response.status_code in {
        401,
        403,
        404
    }

def _authenticated_github_url(repository_url: str, github_token: str | None) -> str:
    """Inject a GitHub access token into HTTPS clone URLs when supplied.

    Args:
        repository_url: Original repository URL.
        github_token: Optional GitHub access token.

    Returns:
        Token-authenticated clone URL when possible, otherwise the original URL.
    """
    token = (github_token or "").strip()
    if not token:
        return repository_url

    split = urlsplit(repository_url)
    if split.scheme not in {"http", "https"} or split.hostname != "github.com":
        return repository_url

    netloc = f"x-access-token:{quote(token, safe='')}@{split.netloc}"
    return urlunsplit((split.scheme, netloc, split.path, split.query, split.fragment))

def _safe_clone_error(message: str, github_token: str | None) -> str:
    """Redact and normalize clone errors before exposing them to the API caller.

    Args:
        message: Raw clone error message.
        github_token: Optional token that must be redacted if present.

    Returns:
        Sanitized, compact clone error message.
    """
    token = (github_token or "").strip()
    if token:
        message = message.replace(token, "<redacted-token>")
        message = re.sub(r"x-access-token:[^@\\s]+@", "x-access-token:<redacted-token>@", message)

    normalized = message.lower()
    if "filename too long" in normalized or "unable to checkout working tree" in normalized:
        return (
            "repository contains file paths that are too long for Windows checkout. "
            "Enable long paths in Windows/Git or upload a cleaned source folder without build output directories."
        )
    if "authentication failed" in normalized or "could not read username" in normalized:
        return "repository authentication failed. Provide a GitHub access token with read access and try again."
    if "repository not found" in normalized:
        return "repository was not found. Check the owner, repository name, and access permissions."
    if "timed out" in normalized or "timeout" in normalized:
        return "repository clone timed out. Try again or upload a project ZIP directly."

    compact = " ".join(message.split())
    if len(compact) > 240:
        return f"{compact[:237]}..."
    return compact

def analyze_local_repository(root: Path, source_name: str, migration_requirements: MigrationRequirements
) -> tuple[RepositoryAnalysis, list[str]]:
    """Analyze a local project directory and return repository findings.

    Args:
        root: Root directory of the uploaded or extracted project.
        source_name: Display name for the source being analyzed.
        migration_requirements: User-selected migration requirements.

    Returns:
        Repository analysis and warnings produced during local scanning.
    """
    warnings: list[str] = []

    try:
        warnings.append(f"Analysis started for {source_name}")
        files = list(_iter_repo_files(root))
        detected_files = [str(path.relative_to(root)).replace("\\", "/") for path in files]
        evidence = _collect_evidence(files, root)
        fallback = _infer_repository_analysis(detected_files, evidence)
        analysis, llm_warnings = analyze_repository_evidence(
            fallback,
            migration_requirements
        )
        warnings.extend(llm_warnings)
        return _merge_analysis(fallback, analysis), warnings
    except Exception as exc:
        warnings.append(f"Folder analysis failed: {exc}")
        return _empty_analysis(), warnings

def _iter_repo_files(root: Path) -> Iterable[Path]:
    """Yield source files while skipping dependency, build, and IDE folders.

    Args:
        root: Repository or project root directory.

    Returns:
        Iterable of file paths that should be considered for analysis.
    """
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part.lower() in IGNORED_PARTS for part in path.relative_to(root).parts):
            continue
        if path.name.lower() in IGNORED_FILE_NAMES:
            continue
        yield path

def _collect_evidence(files: list[Path], root: Path) -> list[dict[str, str]]:
    """Collect bounded, redacted text snippets from the most useful project files.

    Args:
        files: Candidate repository files.
        root: Repository or project root directory.

    Returns:
        List of evidence dictionaries containing relative path and content snippet.
    """
    evidence: list[dict[str, str]] = []
    total_chars = 0
    SKIP_FILES = {
    "readme.md",
    "readme.txt",
    "coverage.xml",
    }
    SKIP_FOLDERS = {
        "tests",
        "test",
        "docs"
    }

    for path in sorted(files, key=_evidence_priority):
        if path.name.lower() in SKIP_FILES:
            continue

        if any(part.lower() in SKIP_FOLDERS for part in path.parts):
            continue
        if len(evidence) >= MAX_EVIDENCE_FILES or total_chars >= MAX_TOTAL_CHARS:
            break
        if path.name.lower() in NON_EVIDENCE_FILE_NAMES:
            continue
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
    """Rank files so manifests, config, CI, and source code are sampled first.

    Args:
        path: Candidate evidence file path.

    Returns:
        Sort key containing priority bucket and normalized path text.
    """
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
    """Return whether a file is small enough and likely safe to read as text.

    Args:
        path: File path to inspect.

    Returns:
        True when the file can be sampled as text; otherwise False.
    """
    if path.stat().st_size > 250_000:
        return False
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".7z", ".exe", ".dll"}:
        return False
    return True

def _redact_sensitive_values(text: str) -> str:
    """Mask common secret patterns before evidence is sent to analysis logic.

    Args:
        text: Source text snippet.

    Returns:
        Text with common credential and token patterns redacted.
    """
    redacted = text
    patterns = [
        r"(?i)(api[_-]?key|secret|password|pwd|token|client[_-]?secret|connection[_-]?string)\s*[:=]\s*['\"]?[^'\"\n]+",
        r"(?i)(authorization:\s*bearer\s+)[a-z0-9._\-]+",
        r"(?i)(defaultendpointsprotocol=.*?accountkey=)[^;\n]+",
    ]
    for pattern in patterns:
        redacted = re.sub(pattern, lambda match: f"{match.group(1)}=<redacted>", redacted)
    return redacted

def _infer_repository_analysis(detected_files: list[str], evidence: list[dict[str, str]]) -> RepositoryAnalysis:
    """Infer technology stack and architecture signals from filenames and snippets.

    Args:
        detected_files: Relative file paths discovered in the repository.
        evidence: Sampled source/config snippets from important files.

    Returns:
        Deterministic repository analysis built from local signals.
    """
    paths = [path.replace("\\", "/") for path in detected_files]
    names = {Path(path).name.lower() for path in paths}
    suffixes = {Path(path).suffix.lower() for path in paths}
    evidence_by_path = {item["path"].lower(): item["content"] for item in evidence}
    evidence_text = "\n".join(item["content"] for item in evidence).lower()
    languages: list[str] = []
    frameworks: list[str] = []
    runtimes: list[str] = []
    package_managers: list[str] = []
    databases: list[str] = []
    containers: list[str] = []
    infrastructure: list[str] = []
    cicd: list[str] = []
    cloud_dependencies: list[str] = []
    external_dependencies: list[str] = []

    _append_if(languages, ".py" in suffixes, "Python")
    _append_if(languages, bool({".js", ".jsx"} & suffixes), "JavaScript")
    _append_if(languages, bool({".ts", ".tsx"} & suffixes), "TypeScript")
    _append_if(languages, ".cs" in suffixes, "C#")
    _append_if(languages, ".java" in suffixes, "Java")
    _append_if(languages, ".go" in suffixes, "Go")

    _append_if(package_managers, "package.json" in names, "npm")
    _append_if(package_managers, "yarn.lock" in names, "Yarn")
    _append_if(package_managers, "pnpm-lock.yaml" in names, "pnpm")
    _append_if(package_managers, "requirements.txt" in names or "pyproject.toml" in names, "pip")
    _append_if(package_managers, "pom.xml" in names, "Maven")
    _append_if(package_managers, "build.gradle" in names, "Gradle")

    package_names = _package_json_dependencies(evidence_by_path)
    python_packages = _python_dependencies(evidence_by_path)
    has_django_project = (
        "django" in python_packages
        or "from django" in evidence_text
        or "import django" in evidence_text
        or "django.contrib" in evidence_text
        or "manage.py" in names
        or any(path.endswith("/settings.py") for path in paths)
        or any(path.endswith("/urls.py") and "/django/" in path.lower() for path in paths)
        or any(path.endswith("/wsgi.py") or path.endswith("/asgi.py") for path in paths)
    )

    _append_if(frameworks, "react" in package_names or any(path.endswith(".tsx") for path in paths), "React")
    _append_if(frameworks, "vite" in package_names or "vite.config.ts" in names or "vite.config.js" in names, "Vite")
    _append_if(frameworks, "next" in package_names or "next.config.js" in names or "next.config.ts" in names, "Next.js")
    _append_if(frameworks, "fastapi" in python_packages or "from fastapi" in evidence_text or "import fastapi" in evidence_text, "FastAPI")
    _append_if(frameworks, "flask" in python_packages or "from flask" in evidence_text, "Flask")
    _append_if(frameworks, has_django_project, "Django")
    _append_if(frameworks, "express" in package_names, "Express")
    _append_if(frameworks, "spring-boot" in evidence_text or "springframework" in evidence_text, "Spring Boot")
    _append_if(frameworks, "azure-functions" in python_packages or "function.json" in names or "host.json" in names, "Azure Functions")

    _append_if(runtimes, "package.json" in names or "package-lock.json" in names or "yarn.lock" in names,"Node.js" )
    _append_if(runtimes, ".py" in suffixes or "requirements.txt" in names or "pyproject.toml" in names, "Python")
    _append_if(runtimes, ".cs" in suffixes, ".NET")
    _append_if(runtimes, ".java" in suffixes, "JVM")
    _append_if(
    databases,
    "sqlserver" in evidence_text
    or "microsoft.entityframeworkcore.sqlserver" in evidence_text,
    "SQL Server"
)
    is_dotnet_project = (
        ".cs" in suffixes
        or "asp.net" in evidence_text
        or "microsoft.entityframeworkcore" in evidence_text
    )
    _append_if(
        frameworks,
        is_dotnet_project
        and (
            "dbcontext" in evidence_text
            or "entityframeworkcore" in evidence_text
            or any("/migrations/" in path.lower() for path in paths)
        ),
        "Entity Framework Core",
    )
    _append_if(
        frameworks,
        is_dotnet_project
        and (
            "addcontrollers" in evidence_text
            or "addcontrollerswithviews" in evidence_text
            or any("/controllers/" in path.lower() for path in paths)
        ),
        "ASP.NET Core",
    )

    _append_if(
        frameworks,
        is_dotnet_project and any("/views/" in path.lower() for path in paths),
        "ASP.NET Core MVC",
    )

    _append_if(databases, _has_database_signal("mongodb", package_names, python_packages, evidence_text), "MongoDB")
    _append_if(databases, _has_database_signal("postgresql", package_names, python_packages, evidence_text), "PostgreSQL")
    _append_if(databases, _has_database_signal("mysql", package_names, python_packages, evidence_text), "MySQL")
    _append_if(databases, _has_database_signal("redis", package_names, python_packages, evidence_text), "Redis")
    _append_if(databases, _has_database_signal("sqlite", package_names, python_packages, evidence_text), "SQLite")

    _append_if(containers, "dockerfile" in names, "Dockerfile")
    _append_if(containers, "docker-compose.yml" in names or "docker-compose.yaml" in names, "Docker Compose")
    _append_if(infrastructure, any(path.endswith(".tf") for path in paths), "Terraform")
    _append_if(cicd, any(".github/workflows/" in path.lower() for path in paths), "GitHub Actions")
    _append_if(cicd, "azure-pipelines.yml" in names, "Azure Pipelines")
    _append_if(cicd, ".gitlab-ci.yml" in names, "GitLab CI")
    _append_if(
        cloud_dependencies,
        "datafactory" in evidence_text
        or "data factory" in evidence_text
        or "azure.datafactory" in evidence_text
        or "microsoft.datafactory" in evidence_text
        or any("datafactory" in path.lower() or "data-factory" in path.lower() for path in paths),
        "Azure Data Factory",
    )
    _append_if(
        cloud_dependencies,
        "servicebus" in evidence_text
        or "service bus" in evidence_text
        or "azure.servicebus" in evidence_text
        or "microsoft.servicebus" in evidence_text,
        "Azure Service Bus",
    )
    _append_if(
        cloud_dependencies,
        "eventhub" in evidence_text
        or "event hub" in evidence_text
        or "azure.eventhub" in evidence_text
        or "microsoft.eventhub" in evidence_text,
        "Azure Event Hubs",
    )
    _append_if(
        cloud_dependencies,
        "applicationinsights" in evidence_text
        or "application insights" in evidence_text
        or "microsoft.applicationinsights" in evidence_text,
        "Azure Application Insights",
    )
    _append_if(
        external_dependencies,
        "salesforce" in evidence_text,
        "Salesforce",
    )

    hosting_model = "Serverless" if "Azure Functions" in frameworks else "Containerized" if containers else "Application server"
    deployment_model = "Docker" if containers else "Unknown"
    architecture_pattern = _architecture_pattern(frameworks, databases)
    application_type = (
        "Web Application"
        if any(item in frameworks for item in [
            "React",
            "Next.js",
            "FastAPI",
            "Flask",
            "Django",
            "Express",
            "ASP.NET Core",
            "ASP.NET Core MVC"
        ])
        else "Application"
    )
    dependency_graph = _build_dependency_graph(
        frameworks,
        runtimes,
        databases,
        cloud_dependencies,
        external_dependencies,
    )

    return RepositoryAnalysis(
        project_summary=_project_summary(application_type, architecture_pattern, languages, frameworks, runtimes, databases, package_managers, containers),
        languages=languages,
        frameworks=frameworks,
        runtimes=runtimes,
        hosting_model=hosting_model,
        deployment_model=deployment_model,
        triggers=["HTTP"] if application_type == "Web Application" else [],
        databases=databases,
        package_managers=package_managers,
        container_configs=containers,
        infrastructure_configs=infrastructure,
        cicd_configs=cicd,
        external_dependencies=external_dependencies,
        cloud_dependencies=cloud_dependencies,
        dependency_graph=dependency_graph,
        architecture_pattern=architecture_pattern,
        application_type=application_type,
        stateful_services=databases,
        storage_dependencies=[],
        network_requirements=["HTTP/HTTPS"] if application_type == "Web Application" else [],
        governance_findings=[],
        detected_files=detected_files[:80],
    )

def _merge_analysis(
    fallback: RepositoryAnalysis,
    analysis: RepositoryAnalysis
) -> RepositoryAnalysis:
    """Merge LLM analysis with deterministic fallback signals.

    Args:
        fallback: Deterministic repository analysis.
        analysis: LLM-enhanced repository analysis.

    Returns:
        Combined repository analysis with fallback values preserved when needed.
    """

    data = analysis.model_dump()
    fallback_data = fallback.model_dump()

    for key, value in fallback_data.items():

        current = data.get(key)

        if isinstance(value, list):
            data[key] = _dedupe(
                [*(current or []), *value]
            )

        elif current in (None, "", "Unknown"):
            if value not in (None, "", "Unknown"):
                data[key] = value

    data["dependency_graph"] = _sanitize_dependency_graph(
        data.get("dependency_graph") or [],
        data.get("package_managers") or [],
    )

    return RepositoryAnalysis.model_validate(data)

def _append_if(items: list[str], condition: bool, value: str) -> None:
    """Append a value once when the supplied condition is true.

    Args:
        items: List to mutate.
        condition: Whether the value should be appended.
        value: Value to append when it is not already present.

    Returns:
        None.
    """
    if condition and value not in items:
        items.append(value)

def _dedupe(items: list[str]) -> list[str]:
    """Return non-empty items while preserving first-seen order.

    Args:
        items: Items to deduplicate.

    Returns:
        Ordered list of unique non-empty strings.
    """
    return list(dict.fromkeys(item for item in items if item))

def _build_dependency_graph(
    frameworks: list[str],
    runtimes: list[str],
    databases: list[str],
    cloud_dependencies: list[str],
    external_dependencies: list[str],
) -> list[str]:
    """Build a simple application-to-dependency graph from detected signals.

    Args:
        frameworks: Detected application frameworks.
        runtimes: Detected runtime platforms.
        databases: Detected databases.
        cloud_dependencies: Detected cloud service dependencies.
        external_dependencies: Detected third-party dependencies.

    Returns:
        Dependency graph entries in "Application -> dependency" format.
    """
    dependency_targets = frameworks + runtimes + databases + cloud_dependencies + external_dependencies
    return [f"Application -> {item}" for item in _dedupe(dependency_targets)]

def _sanitize_dependency_graph(
    dependency_graph: list[str],
    package_managers: list[str],
) -> list[str]:
    """Remove package managers from dependency graph entries.

    Args:
        dependency_graph: Raw dependency graph entries.
        package_managers: Detected package managers that should not be graph dependencies.

    Returns:
        Sanitized dependency graph entries.
    """
    package_manager_names = {item.strip().lower() for item in package_managers}
    sanitized: list[str] = []

    for dependency in dependency_graph:
        target = dependency.split("->")[-1].strip().lower()
        if target in package_manager_names:
            continue
        sanitized.append(dependency)

    return _dedupe(sanitized)

def _architecture_pattern(frameworks: list[str], databases: list[str]) -> str:
    """Classify the broad application architecture from framework and data signals.

    Args:
        frameworks: Detected application frameworks.
        databases: Detected databases.

    Returns:
        Human-readable architecture pattern.
    """
    if "Azure Functions" in frameworks:
        return "Serverless event-driven application"
    if "Django" in frameworks and databases:
        return "Stateful Django web application"
    if "Django" in frameworks:
        return "Django web application"
    if any(item in frameworks for item in ["React", "Next.js"]) and any(item in frameworks for item in ["FastAPI", "Flask", "Django", "Express", "Spring Boot"]):
        return "Full-stack web application"
    if databases:
        return "Stateful web/API application"
    return "Web/API application"

def _package_json_dependencies(evidence_by_path: dict[str, str]) -> set[str]:
    """Extract dependency names from sampled package.json files.

    Args:
        evidence_by_path: Mapping of relative evidence path to sampled content.

    Returns:
        Lowercase package names declared in package.json files.
    """
    packages: set[str] = set()
    for path, content in evidence_by_path.items():
        if not path.endswith("package.json"):
            continue
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue
        for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            values = data.get(section, {})
            if isinstance(values, dict):
                packages.update(name.lower() for name in values)
    return packages

def _python_dependencies(evidence_by_path: dict[str, str]) -> set[str]:
    """Extract Python dependency names from sampled requirements and pyproject files.

    Args:
        evidence_by_path: Mapping of relative evidence path to sampled content.

    Returns:
        Lowercase Python package names.
    """
    packages: set[str] = set()
    for path, content in evidence_by_path.items():
        if path.endswith("requirements.txt"):
            for line in content.splitlines():
                package = re.split(r"[<>=~!;\[]", line.strip(), maxsplit=1)[0].strip()
                if package and not package.startswith(("#", "-")):
                    packages.add(package.lower())
        elif path.endswith("pyproject.toml"):
            packages.update(match.lower() for match in re.findall(r'["\']([A-Za-z0-9_.-]+)[<>=~!;\[]', content))
    return packages

def _project_summary(
    application_type: str,
    architecture_pattern: str,
    languages: list[str],
    frameworks: list[str],
    runtimes: list[str],
    databases: list[str],
    package_managers: list[str],
    containers: list[str],
) -> str:
    """Compose a short human-readable project summary from detected stack data.

    Args:
        application_type: Detected application type.
        architecture_pattern: Detected architecture pattern.
        languages: Detected programming languages.
        frameworks: Detected frameworks.
        runtimes: Detected runtime platforms.
        databases: Detected databases.
        package_managers: Detected package managers.
        containers: Detected container configuration files.

    Returns:
        One-sentence project summary.
    """
    stack = _dedupe([*frameworks, *runtimes, *languages])
    parts = [
        f"{application_type} using {_human_list(stack) if stack else 'an undetected application stack'}",
        f"with {architecture_pattern.lower()}",
    ]
    if databases:
        parts.append(f"and data dependencies on {_human_list(databases)}")
    if package_managers:
        parts.append(f"managed with {_human_list(package_managers)}")
    if containers:
        parts.append(f"including {_human_list(containers)} container configuration")
    return " ".join(parts) + "."

def _has_database_signal(database: str, package_names: set[str], python_packages: set[str], evidence_text: str) -> bool:
    """Return whether package names or text patterns indicate a database dependency.

    Args:
        database: Database key to check.
        package_names: Detected JavaScript package names.
        python_packages: Detected Python package names.
        evidence_text: Lowercase combined evidence text.

    Returns:
        True when dependency or text evidence matches the database; otherwise False.
    """
    signals = {
        "mongodb": {
            "packages": {"mongodb", "mongoose", "pymongo", "motor"},
            "patterns": [r"mongodb(?:\+srv)?:\/\/", r"\bmongo_uri\b", r"\bmongodb_uri\b"],
        },
        "postgresql": {
            "packages": {"pg", "postgres", "postgresql", "psycopg", "psycopg2", "asyncpg", "pg-promise"},
            "patterns": [r"postgres(?:ql)?:\/\/", r"\bpostgres_host\b", r"\bpostgres_db\b", r"\bpostgres_user\b"],
        },
        "mysql": {
            "packages": {"mysql", "mysql2", "pymysql", "mysqlclient", "aiomysql"},
            "patterns": [r"mysql:\/\/", r"\bmysql_host\b", r"\bmysql_database\b", r"\bmysql_user\b"],
        },
        "redis": {
            "packages": {"redis", "ioredis", "aioredis"},
            "patterns": [r"redis:\/\/", r"\bredis_url\b", r"\bredis_host\b"],
        },
        "sqlite": {
            "packages": {"sqlite3", "better-sqlite3", "aiosqlite"},
            "patterns": [r"sqlite:\/\/", r"\.sqlite\b", r"\.db\b"],
        },
    }
    database_signals = signals[database]
    if package_names & database_signals["packages"] or python_packages & database_signals["packages"]:
        return True
    return any(re.search(pattern, evidence_text) for pattern in database_signals["patterns"])

def _human_list(items: list[str]) -> str:
    """Format a list into a compact phrase for blueprint text.

    Args:
        items: Values to format.

    Returns:
        Human-readable list phrase or "Not detected".
    """
    if not items:
        return "Not detected"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"

def _empty_analysis() -> RepositoryAnalysis:
    """Return an empty repository analysis used when scanning cannot proceed.

    Args:
        None.

    Returns:
        Repository analysis populated with unknown or empty values.
    """
    return RepositoryAnalysis(
        project_summary="Unknown",
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
