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
    warnings: list[str] = []
    temp_root = Path(__file__).resolve().parents[2] / ".tmp" / "repo-clones"
    temp_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(
    tempfile.mkdtemp(
        prefix="infraguide-",
        dir=temp_root
    )
)
    
    print("Repository URL:", repository_url)
    print("Token supplied:", bool(github_token))

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
        print("CLONE SUCCESSFUL")
        print("Repository cloned to:", tmp_dir)
        files = list(_iter_repo_files(tmp_dir))
        # print("BEFORE SUBPROCESS")

        # result = subprocess.run(
        #     ["git", "config", "--list"],
        #     capture_output=True,
        #     text=True
        # )

        # print("AFTER SUBPROCESS")

        # print(result.stdout)
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
        print("CLONE ERROR:", exc)
        warnings.append(f"Repository clone failed: {_safe_clone_error(str(exc), github_token)}")
        return _empty_analysis(), warnings
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _non_interactive_git_env() -> dict[str, str]:
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
    token = (github_token or "").strip()
    if not token:
        return repository_url

    split = urlsplit(repository_url)
    if split.scheme not in {"http", "https"} or split.hostname != "github.com":
        return repository_url

    netloc = f"x-access-token:{quote(token, safe='')}@{split.netloc}"
    return urlunsplit((split.scheme, netloc, split.path, split.query, split.fragment))


def _safe_clone_error(message: str, github_token: str | None) -> str:
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
        return "repository clone timed out. Try again or upload the project folder directly."

    compact = " ".join(message.split())
    if len(compact) > 240:
        return f"{compact[:237]}..."
    return compact


def analyze_local_repository(root: Path, source_name: str, migration_requirements: MigrationRequirements
) -> tuple[RepositoryAnalysis, list[str]]:
    warnings: list[str] = []

    try:
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
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part.lower() in IGNORED_PARTS for part in path.relative_to(root).parts):
            continue
        if path.name.lower() in IGNORED_FILE_NAMES:
            continue
        yield path


def _collect_evidence(files: list[Path], root: Path) -> list[dict[str, str]]:
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
        relative_path = str(path.relative_to(root)).replace("\\", "/")

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


def _infer_repository_analysis(detected_files: list[str], evidence: list[dict[str, str]]) -> RepositoryAnalysis:
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

    _append_if(frameworks, "react" in package_names or any(path.endswith(".tsx") for path in paths), "React")
    _append_if(frameworks, "vite" in package_names or "vite.config.ts" in names or "vite.config.js" in names, "Vite")
    _append_if(frameworks, "next" in package_names or "next.config.js" in names or "next.config.ts" in names, "Next.js")
    _append_if(frameworks, "fastapi" in python_packages or "from fastapi" in evidence_text or "import fastapi" in evidence_text, "FastAPI")
    _append_if(frameworks, "flask" in python_packages or "from flask" in evidence_text, "Flask")
    _append_if(frameworks, "django" in python_packages or "django" in python_packages, "Django")
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
    dependency_graph = [f"Application -> {item}" for item in frameworks + runtimes + databases + package_managers + cloud_dependencies + external_dependencies]

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

    return RepositoryAnalysis.model_validate(data)


def _append_if(items: list[str], condition: bool, value: str) -> None:
    if condition and value not in items:
        items.append(value)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _architecture_pattern(frameworks: list[str], databases: list[str]) -> str:
    if "Azure Functions" in frameworks:
        return "Serverless event-driven application"
    if any(item in frameworks for item in ["React", "Next.js"]) and any(item in frameworks for item in ["FastAPI", "Flask", "Django", "Express", "Spring Boot"]):
        return "Full-stack web application"
    if databases:
        return "Stateful web/API application"
    return "Web/API application"


def _package_json_dependencies(evidence_by_path: dict[str, str]) -> set[str]:
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
    if not items:
        return "Not detected"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _empty_analysis() -> RepositoryAnalysis:
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
