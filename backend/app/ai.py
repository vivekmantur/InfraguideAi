from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import DEFAULT_MODEL, GROQ_API_KEY, GROQ_ENDPOINT
from .models import AssessmentResponse, ChatMessage, CloudSizingRequirements, MigrationRequirements, RepositoryAnalysis,MigrationStrategyResult


AWS_PRICING_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "ca-central-1",
    "sa-east-1",
    "eu-west-1",
    "eu-west-2",
    "eu-central-1",
    "eu-north-1",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
]


def groq_model() -> str:
    return DEFAULT_MODEL


def is_groq_configured() -> bool:
    return bool(GROQ_API_KEY)


def analyze_repository_evidence(
    fallback: RepositoryAnalysis,
    requirements: MigrationRequirements
) -> tuple[RepositoryAnalysis, list[str]]:
    warnings: list[str] = []

    if not is_groq_configured():
        warnings.append(
            "Groq is not configured. Add GROQ_API_KEY to backend/.env for LLM repository analysis."
        )
        return fallback, warnings

    prompt = f"""
Repository Facts:

{json.dumps(fallback.model_dump(), indent=2)}

Migration Requirements:

Cloud Provider: {requirements.cloud_provider}
Traffic: {requirements.expected_traffic}
Budget: {requirements.budget_preference}
Goal: {requirements.migration_goal}
Timeline: {requirements.migration_timeline}

Based ONLY on the facts above determine:

1. Improved project summary
2. Architecture pattern
3. Governance findings
4. Migration complexity

Additionally estimate cloud sizing requirements.

Sizing Rules:

- Small utility/service applications:
  CPU: 2-4 cores
  Memory: 4-8 GB

- Medium web APIs:
  CPU: 4-8 cores
  Memory: 8-16 GB

- Enterprise APIs / Microservices:
  CPU: 8-16 cores
  Memory: 16-32 GB

- If database size is unknown:
  estimate conservatively.

- If traffic is low:
  smaller sizing.

- If traffic is medium:
  medium sizing.

- If traffic is high:
  larger sizing.

Do not guess aggressively.
Use confidence = Low, Medium, or High.

Do not infer containerization unless Docker, Kubernetes,
Container Apps, AKS, ECS, EKS, Cloud Run, or container
artifacts are detected.

Return JSON:
{{
  "project_summary": "",
  "architecture_pattern": "",
  "governance_findings": [],
  "migration_complexity": "",

  "cloud_sizing": {{
    "application_type": "",
    "cpu_cores": 0,
    "memory_gb": 0,
    "storage_gb": 0,
    "database_type": "",
    "database_size_gb": 0,
    "requires_load_balancer": false,
    "requires_containerization": false,
    "confidence": ""
  }}
}}
"""

    print("Prompt size:", len(prompt))
    print(json.dumps(fallback.model_dump(), indent=2))

    raw = _chat_completion(
        [
            {
                "role": "system",
                "content": "You return strict JSON only. No markdown.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        fallback="{}",
        temperature=0.1,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )

    print("LLM Content:", raw)

    try:
        data = _load_json_object(raw)       

        print("PARSED JSON")
        print(json.dumps(data, indent=2))

        if not data:
            warnings.append(
                "LLM repository analysis returned an empty response. Using local repository analysis."
            )
            return fallback, warnings

        merged = fallback.model_copy(deep=True)

        if data.get("project_summary"):
            merged.project_summary = data["project_summary"]

        if data.get("architecture_pattern"):
            merged.architecture_pattern = data["architecture_pattern"]

        if data.get("governance_findings"):
            merged.governance_findings = data["governance_findings"]

        if data.get("cloud_sizing"):
            merged.cloud_sizing = CloudSizingRequirements.model_validate(
                data["cloud_sizing"]
            )

        return merged, warnings

    except Exception as exc:
        warnings.append(
            f"LLM repository analysis failed: {exc}. Raw response preview: {_safe_preview(raw)}"
        )
        return fallback, warnings

def generate_architect_reasoning(
    analysis: RepositoryAnalysis,
    provider: str,
    services: list[dict[str, str]],
    cost: dict[str, Any],
    roadmap: list[str],
    strategy: MigrationStrategyResult
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

Cloud Sizing:
- CPU Cores: {analysis.cloud_sizing.cpu_cores if analysis.cloud_sizing else "Unknown"}
- Memory: {analysis.cloud_sizing.memory_gb if analysis.cloud_sizing else "Unknown"} GB
- Storage: {analysis.cloud_sizing.storage_gb if analysis.cloud_sizing else "Unknown"} GB
- Load Balancer: {analysis.cloud_sizing.requires_load_balancer if analysis.cloud_sizing else "Unknown"}
- Containerization: {analysis.cloud_sizing.requires_containerization if analysis.cloud_sizing else "Unknown"}

Recommended Migration Strategy:
- Strategy: {strategy.strategy}
- Confidence: {strategy.confidence}

Evidence:
{chr(10).join(f"- {r}" for r in strategy.reasons)}

Recommended provider: {provider}
Recommended services: {services}
Cost estimate: {cost}
Roadmap: {roadmap}

Write 2-3 professional paragraphs.

Explain:
- Why the selected migration strategy is appropriate.
- How the repository architecture influenced the recommendation.
- What business value the organization will gain.
- Key migration risks and considerations.

Requirements:
- Write in complete sentences and paragraphs.
- Do not use headings.
- Do not use bullet points.
- Do not repeat the evidence list verbatim.
- Do not suggest a different migration strategy.
- Do not contradict the selected migration strategy.
- Write like a senior cloud architect preparing an executive migration assessment.
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


def generate_aws_pricing_estimate(
    analysis: RepositoryAnalysis,
    requirements: MigrationRequirements,
    services: list[dict[str, str]],
    cloud_sizing: CloudSizingRequirements,
) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []

    if not is_groq_configured():
        warnings.append(
            "Groq is not configured. Falling back to heuristic AWS pricing."
        )
        return None, warnings

    pricing_facts = {
        "project_summary": analysis.project_summary,
        "languages": analysis.languages,
        "frameworks": analysis.frameworks,
        "runtimes": analysis.runtimes,
        "hosting_model": analysis.hosting_model,
        "deployment_model": analysis.deployment_model,
        "databases": analysis.databases,
        "container_configs": analysis.container_configs,
        "application_type": analysis.application_type,
        "architecture_pattern": analysis.architecture_pattern,
        "cloud_dependencies": analysis.cloud_dependencies,
        "storage_dependencies": analysis.storage_dependencies,
    }

    prompt = f"""
You are estimating AWS migration pricing for a single application.

Repository facts:
{json.dumps(pricing_facts, indent=2)}

Migration requirements:
- Cloud provider: AWS
- Traffic: {requirements.expected_traffic.value}
- Budget: {requirements.budget_preference.value}
- Goal: {requirements.migration_goal.value}
- Timeline: {requirements.migration_timeline.value}

Recommended services:
{json.dumps(services, indent=2)}

Sizing:
{json.dumps(cloud_sizing.model_dump(), indent=2)}

Estimate AWS on-demand monthly pricing for these regions only:
{json.dumps(AWS_PRICING_REGIONS)}

Rules:
- Use USD.
- Include application runtime and the recommended managed services.
- Use conservative but realistic estimates based on current public AWS pricing patterns.
- Runtime should reflect the recommended runtime service, such as ECS Fargate or Lambda.
- Database should reflect the recommended managed database if a database service is present.
- Storage, secrets, and monitoring should be included when present.
- Return one row for every listed region.
- Vary prices by region where appropriate.
- Keep monitoring or secrets similar across regions only if they are effectively global or near-global in pricing.
- Do not use INR.
- Do not include markdown.

Return strict JSON only in this shape:
{{
  "currency": "USD",
  "line_items": [],
  "assumptions": [],
  "regional_prices": [
    {{
      "provider": "AWS",
      "region": "us-east-1",
      "currency": "USD",
      "runtime_sku": "",
      "runtime_monthly": 0,
      "services_monthly": 0,
      "total_monthly": 0,
      "source": "Groq AWS estimate",
      "service_breakdown": [
        {{
          "component": "Database",
          "recommended": "Amazon RDS",
          "currency": "USD",
          "monthly_cost": 0,
          "source": "Groq AWS estimate"
        }}
      ]
    }}
  ]
}}
"""

    raw = _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You return strict JSON only. "
                    "No markdown. No commentary."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        fallback="{}",
        temperature=0.15,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )

    try:
        data = _load_json_object(raw)
    except Exception as exc:
        warnings.append(
            f"AWS pricing LLM response could not be parsed: {exc}. "
            f"Raw response preview: {_safe_preview(raw)}"
        )
        return None, warnings

    regional_prices = data.get(
        "regional_prices",
        []
    )

    if not isinstance(regional_prices, list) or not regional_prices:
        warnings.append(
            "AWS pricing LLM response did not include regional prices."
        )
        return None, warnings

    return data, warnings


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
    api_key = GROQ_API_KEY
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
        with httpx.Client(timeout=90) as client:
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


def _load_json_object(content: str) -> dict[str, Any]:
    payload = _json_payload(content)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        start = payload.find("{")
        if start == -1:
            raise
        data, _ = decoder.raw_decode(payload[start:])

    if not isinstance(data, dict):
        raise ValueError("LLM response JSON must be an object.")
    return data


def _safe_preview(content: str) -> str:
    compact = " ".join(content.split())
    return compact[:180]


def _empty_repository_analysis(detected_files: list[str]) -> RepositoryAnalysis:
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
