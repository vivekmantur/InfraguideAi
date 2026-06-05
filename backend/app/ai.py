from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

import httpx
from dotenv import load_dotenv

from .models import AssessmentResponse, ChatMessage, RepositoryAnalysis

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
BACKEND_ENV = Path(__file__).resolve().parents[1] / ".env"

load_dotenv(BACKEND_ENV)


def groq_model() -> str:
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL)


def is_groq_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def analyze_repository_evidence(
    repository_url: str,
    detected_files: list[str],
    evidence: list[dict[str, str]],
) -> tuple[RepositoryAnalysis, list[str]]:
    warnings: list[str] = []
    if not is_groq_configured():
        warnings.append("Groq is not configured. Add GROQ_API_KEY to backend/.env for LLM repository analysis.")
        return _empty_repository_analysis(detected_files), warnings

    schema = RepositoryAnalysis.model_json_schema()
    prompt = f"""
You are an expert cloud migration discovery engine. Analyze the repository evidence and infer the application architecture.

Repository URL:
{repository_url}

Detected file paths:
{json.dumps(detected_files[:200], indent=2)}

Repository evidence:
{json.dumps(evidence, indent=2)}

Return ONLY valid JSON matching this schema:
{json.dumps(schema, indent=2)}

Rules:
- Do not invent technologies that are not supported by file names, manifests, imports, config, bindings, or code evidence.
- Prefer precise cloud/runtime terms, for example Azure Functions, Python 3.11, HTTP Trigger, Timer Trigger, Azure Function App.
- If evidence is weak, use empty arrays and "Unknown" rather than guessing.
- external_dependencies means third-party services or APIs, not package libraries.
- dependency_graph must include separate edges for confirmed runtime, framework, trigger, cloud service, database, storage, package manager, and external API dependencies.
- governance_findings should include security risks found from evidence, but do not quote secret values.
- dependency_graph should use concise edges like "Application -> Azure Functions Runtime".
"""

    raw = _chat_completion(
        [
            {"role": "system", "content": "You return strict JSON for repository architecture analysis. No markdown."},
            {"role": "user", "content": prompt},
        ],
        fallback="{}",
        temperature=0.1,
        max_tokens=2200,
        response_format={"type": "json_object"},
    )

    try:
        data = json.loads(_json_payload(raw))
        if not data.get("detected_files"):
            data["detected_files"] = detected_files[:80]
        return RepositoryAnalysis.model_validate(data), warnings
    except Exception as exc:
        warnings.append(f"LLM repository analysis failed: {exc}")
        return _empty_repository_analysis(detected_files), warnings


def generate_architect_reasoning(
    analysis: RepositoryAnalysis,
    provider: str,
    services: list[dict[str, str]],
    cost: dict[str, Any],
    roadmap: list[str],
) -> str:
    fallback = _fallback_reasoning(analysis, provider)
    if not is_groq_configured():
        return fallback

    prompt = f"""
You are a senior cloud migration architect. Explain this recommendation in a concise, enterprise-ready way.

Discovered application:
- Languages: {', '.join(analysis.languages) or 'Not detected'}
- Frameworks: {', '.join(analysis.frameworks) or 'Not detected'}
- Runtime: {', '.join(analysis.runtimes) or 'Not detected'}
- Hosting model: {analysis.hosting_model}
- Deployment model: {analysis.deployment_model}
- Triggers: {', '.join(analysis.triggers) or 'None detected'}
- Databases: {', '.join(analysis.databases) or 'Not detected'}
- Architecture: {analysis.application_type}
- Cloud dependencies: {', '.join(analysis.cloud_dependencies) or 'None detected'}
- Stateful services: {', '.join(analysis.stateful_services) or 'None detected'}
- Governance findings: {', '.join(analysis.governance_findings) or 'None detected'}

Recommended provider: {provider}
Recommended services: {services}
Cost estimate: {cost}
Roadmap: {roadmap}

Return 3 short paragraphs: recommendation, business reason, migration caution.
"""
    return _chat(
        [
            {"role": "system", "content": "You write practical cloud migration guidance for IT leaders and architects."},
            {"role": "user", "content": prompt},
        ],
        fallback=fallback,
        temperature=0.25,
    )


def answer_migration_question(assessment: AssessmentResponse, message: str, history: list[ChatMessage]) -> str:
    fallback = "Groq is not configured yet. Add GROQ_API_KEY on the backend to enable the AI migration assistant."
    if not is_groq_configured():
        return fallback

    compact_assessment = assessment.model_dump(mode="json", exclude={"blueprint_markdown"})
    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are InfraGuide AI, a cloud migration assistant. Answer using the assessment context. "
                "Be concise, practical, and mention uncertainty when repository evidence is weak."
            ),
        },
        {"role": "user", "content": f"Assessment context:\n{compact_assessment}"},
    ]
    messages.extend({"role": item.role, "content": item.content} for item in history[-8:])
    messages.append({"role": "user", "content": message})
    return _chat(messages, fallback=fallback, temperature=0.35)


def _chat(messages: list[dict[str, str]], fallback: str, temperature: float) -> str:
    return _chat_completion(
        messages,
        fallback=fallback,
        temperature=temperature,
        max_tokens=700,
        response_format=None,
    )


def _chat_completion(
    messages: list[dict[str, str]],
    fallback: str,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, str] | None,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return fallback

    payload = {
        "model": groq_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                GROQ_ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content or fallback
    except Exception as exc:
        return f"{fallback} AI generation warning: {exc}"


def _json_payload(content: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return content.strip()


def _empty_repository_analysis(detected_files: list[str]) -> RepositoryAnalysis:
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
        detected_files=detected_files[:80],
    )


def _fallback_reasoning(analysis: RepositoryAnalysis, provider: str) -> str:
    stack = ", ".join(analysis.frameworks or analysis.languages) or "the detected application stack"
    database = ", ".join(analysis.databases) or "no confirmed database dependency"
    return (
        f"{provider} is recommended based on {stack}, {database}, readiness signals, and the selected migration goals. "
        "The architecture favors managed runtime, managed data services, centralized secrets, monitoring, and a phased cutover. "
        "Enable GROQ_API_KEY to replace this deterministic explanation with LLM-generated architect reasoning."
    )
