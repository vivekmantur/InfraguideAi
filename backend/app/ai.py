from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import DEFAULT_MODEL, GROQ_API_KEY, GROQ_API_KEY_2, GROQ_ENDPOINT
from .models import AssessmentResponse, ChatMessage, CloudSizingRequirements, GovernanceAssessment, MigrationRequirements, RepositoryAnalysis, ServiceRecommendation,MigrationStrategyResult


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


REQUIREMENT_INTERPRETATION_RULES = """
Requirement interpretation rules:
- Migration Goal controls the target posture:
  - Cost Optimization: prefer rightsizing, serverless/minimum viable managed tiers, budget controls, and cost review steps.
  - Application Modernization: prefer managed runtimes, CI/CD, container/serverless preparation, observability, and refactoring opportunities.
  - Lift-and-Shift: prefer minimal architecture change, VM/app-runtime migration, compatibility validation, and rollback-first execution.
  - Scalability: prefer autoscaling, load balancing/API gateway, peak-load tests, capacity limits, and runbooks.
  - Performance Improvement: prefer larger runtime/database capacity, profiling, performance dashboards, tuning, and latency validation.
- Expected Traffic controls capacity and validation:
  - Low: minimal baseline, smaller runtime assumptions, scale-up triggers, limited HA.
  - Medium: standard production baseline, moderate load testing, normal autoscaling and observability.
  - High: larger capacity, autoscaling, edge protection, peak/soak testing, stronger rollback thresholds.
- Budget Preference controls cost posture:
  - Low Cost: cost controls, smaller viable tiers, region comparison, budget alerts, scheduled rightsizing.
  - Balanced: reliable production defaults with cost/performance tradeoff.
  - Performance Focused: higher-capacity tiers, stronger monitoring, performance validation, less aggressive cost minimization.
- Migration Timeline controls delivery depth and risk:
  - Immediate: reduce scope, avoid optional modernization, require rollback-first cutover and higher risk.
  - 3 Months: phased migration with standard validation and one rehearsal.
  - 6 Months: staged pilot, deeper security review, load testing, cost tuning, runbook handover.
  - Flexible: modernization-first plan, broader hardening, deeper refactor/optimization options.
"""


def groq_model() -> str:
    return DEFAULT_MODEL


def is_groq_configured() -> bool:
    return bool(_groq_api_keys())


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
        label="repository-analysis",
    )

    print("LLM Content:", raw)

    try:
        data = _load_json_object(raw)       

        print("PARSED JSON")
        print(json.dumps(data, indent=2))

        if not data:
            print(
                "LLM repository analysis returned an empty response. "
                "Using local repository analysis."
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
    strategy: MigrationStrategyResult,
    requirements_profile: dict[str, Any] | None = None
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

Derived planning profile:
{json.dumps(requirements_profile or {}, indent=2)}

{REQUIREMENT_INTERPRETATION_RULES}

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
- How the selected traffic, budget, goal, and timeline changed the recommendation.

Requirements:
- Write in complete sentences and paragraphs.
- Do not use headings.
- Do not use bullet points.
- Do not repeat the evidence list verbatim.
- Do not suggest a different migration strategy.
- Do not contradict the selected migration strategy.
- Align sizing, risk, service posture, and roadmap explanation with the derived planning profile.
- Be concrete about real-world impact; avoid generic language that would apply equally to different selected fields.
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


def generate_service_recommendations(
    analysis: RepositoryAnalysis,
    requirements: MigrationRequirements,
    provider: str,
    strategy: MigrationStrategyResult,
    fallback_services: list[ServiceRecommendation],
    requirements_profile: dict[str, Any] | None = None,
) -> tuple[list[ServiceRecommendation], list[str]]:
    warnings: list[str] = []

    if not is_groq_configured():
        warnings.append(
            "Groq is not configured. Using rule-based recommended services."
        )
        return fallback_services, warnings

    service_signals = {
        "application_type": analysis.application_type,
        "architecture_pattern": analysis.architecture_pattern,
        "hosting_model": analysis.hosting_model,
        "deployment_model": analysis.deployment_model,
        "languages": analysis.languages,
        "frameworks": analysis.frameworks,
        "runtimes": analysis.runtimes,
        "databases": analysis.databases,
        "storage_dependencies": analysis.storage_dependencies,
        "cloud_dependencies": analysis.cloud_dependencies,
        "container_configs": analysis.container_configs,
        "infrastructure_configs": analysis.infrastructure_configs,
        "cicd_configs": analysis.cicd_configs,
        "cloud_sizing": analysis.cloud_sizing.model_dump() if analysis.cloud_sizing else None,
        "derived_planning_profile": requirements_profile or {},
    }

    prompt = f"""
You are a senior cloud migration architect. Recommend target cloud services for this application.

Use ONLY the repository facts and service selection signals below. Do not invent detected databases,
queues, caches, container platforms, CI/CD tools, or storage dependencies that are not present.

Repository facts:
{json.dumps(analysis.model_dump(), indent=2)}

Service selection signals:
{json.dumps(service_signals, indent=2)}

Migration requirements:
- Cloud provider: {requirements.cloud_provider.value}
- Goal: {requirements.migration_goal.value}
- Expected traffic: {requirements.expected_traffic.value}
- Budget preference: {requirements.budget_preference.value}
- Timeline: {requirements.migration_timeline.value}

Selected provider: {provider}
Recommended migration strategy:
{json.dumps(strategy.model_dump(), indent=2)}

Derived planning profile:
{json.dumps(requirements_profile or {}, indent=2)}

{REQUIREMENT_INTERPRETATION_RULES}

Return strict JSON only in this shape:
{{
  "recommended_services": [
    {{
      "component": "",
      "current": "",
      "recommended": ""
    }}
  ]
}}

Rules:
- Always include Application Runtime, Secrets, and Monitoring.
- Include Database only when repository facts show a database dependency.
- Include File Storage only when useful for application assets, uploads, static files, or cloud storage migration.
- Add optional services such as API Gateway, CDN/WAF, Cache, Queue, Event Streaming, Container Registry, CI/CD, or Data Integration only when justified by detected facts or migration requirements.
- Use the derived planning profile to decide when to add autoscaling, edge protection, performance monitoring, cost controls, or reduced-scope runtime choices.
- Low traffic and low cost should prefer minimal/serverless/low-cost services when technically reasonable.
- High traffic, scalability, or performance-focused inputs should include capacity, autoscaling, edge protection, or performance monitoring services where relevant.
- Immediate timeline should avoid unnecessary modernization services unless required by the detected architecture.
- Services must visibly differ when the same repository is assessed with meaningfully different goal, traffic, budget, or timeline values.
- Do not add a premium/performance service for Low Cost unless it is required by the detected architecture.
- If repository facts show Azure Data Factory, ADF, ETL, or data pipeline dependencies, include a Data Integration service such as Azure Data Factory, AWS Glue, or Cloud Data Fusion for the selected provider.
- Use concrete {provider} service names.
- Keep component names short and stable.
- Keep current state factual, using "Not detected" when evidence is absent.
- Return 3-8 services.
- Do not use markdown.
"""

    raw = _chat_completion(
        [
            {
                "role": "system",
                "content": "You return strict JSON only. No markdown. No commentary.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        fallback="{}",
        temperature=0.25,
        max_tokens=1200,
        response_format={"type": "json_object"},
        label="service-recommendations",
    )

    try:
        data = _load_json_object(raw)
        service_rows = data.get("recommended_services")
        if not isinstance(service_rows, list):
            warnings.append(
                "LLM service recommendation did not return a service list. Using rule-based services."
            )
            return fallback_services, warnings

        services: list[ServiceRecommendation] = []
        seen_components: set[str] = set()

        for row in service_rows:
            if not isinstance(row, dict):
                continue
            service = ServiceRecommendation.model_validate(row)
            component_key = service.component.strip().lower()
            if not service.component.strip() or component_key in seen_components:
                continue
            seen_components.add(component_key)
            services.append(service)

        if not services:
            warnings.append(
                "LLM service recommendation returned no usable services. Using rule-based services."
            )
            return fallback_services, warnings

        if not any(service.component.lower() == "application runtime" for service in services):
            services.insert(0, fallback_services[0])

        return services[:8], warnings

    except Exception as exc:
        warnings.append(
            f"LLM service recommendation failed: {exc}. Raw response preview: {_safe_preview(raw)}"
        )
        return fallback_services, warnings


def generate_migration_guidance(
    analysis: RepositoryAnalysis,
    requirements: MigrationRequirements,
    provider: str,
    strategy: MigrationStrategyResult,
    services: list[dict[str, str]],
    fallback_governance: GovernanceAssessment,
    fallback_opportunities: list[str],
    fallback_roadmap: list[str],
    requirements_profile: dict[str, Any] | None = None,
) -> tuple[GovernanceAssessment, list[str], list[str], list[str]]:
    warnings: list[str] = []
    security_signals = {
        "governance_findings_from_repository": analysis.governance_findings,
        "package_managers_detected": analysis.package_managers,
        "container_configs_detected": analysis.container_configs,
        "infrastructure_configs_detected": analysis.infrastructure_configs,
        "cicd_configs_detected": analysis.cicd_configs,
        "frameworks_detected": analysis.frameworks,
        "runtimes_detected": analysis.runtimes,
        "databases_detected": analysis.databases,
        "cloud_dependencies_detected": analysis.cloud_dependencies,
        "storage_dependencies_detected": analysis.storage_dependencies,
    }
    migration_signals = {
        "application_type": analysis.application_type,
        "architecture_pattern": analysis.architecture_pattern,
        "hosting_model": analysis.hosting_model,
        "deployment_model": analysis.deployment_model,
        "languages": analysis.languages,
        "frameworks": analysis.frameworks,
        "runtimes": analysis.runtimes,
        "databases": analysis.databases,
        "package_managers": analysis.package_managers,
        "container_configs": analysis.container_configs,
        "infrastructure_configs": analysis.infrastructure_configs,
        "cicd_configs": analysis.cicd_configs,
        "external_dependencies": analysis.external_dependencies,
        "cloud_dependencies": analysis.cloud_dependencies,
        "storage_dependencies": analysis.storage_dependencies,
        "network_requirements": analysis.network_requirements,
        "dependency_graph": analysis.dependency_graph,
        "cloud_sizing": analysis.cloud_sizing.model_dump() if analysis.cloud_sizing else None,
        "derived_planning_profile": requirements_profile or {},
    }

    if not is_groq_configured():
        warnings.append(
            "Groq is not configured. Using rule-based security, modernization, and roadmap guidance."
        )
        return fallback_governance, fallback_opportunities, fallback_roadmap, warnings

    prompt = f"""
You are a senior cloud migration architect. Generate application-specific migration guidance.

Use ONLY the repository facts and evidence signals below. Do not invent detected files,
tools, databases, CI/CD systems, containers, or secrets that are not present in the facts.

Repository facts:
{json.dumps(analysis.model_dump(), indent=2)}

Migration requirements:
- Cloud provider: {requirements.cloud_provider.value}
- Goal: {requirements.migration_goal.value}
- Expected traffic: {requirements.expected_traffic.value}
- Budget preference: {requirements.budget_preference.value}
- Timeline: {requirements.migration_timeline.value}

Selected provider: {provider}
Recommended migration strategy:
{json.dumps(strategy.model_dump(), indent=2)}

Recommended services:
{json.dumps(services, indent=2)}

Derived planning profile:
{json.dumps(requirements_profile or {}, indent=2)}

{REQUIREMENT_INTERPRETATION_RULES}

Security evidence signals:
{json.dumps(security_signals, indent=2)}

Migration planning signals:
{json.dumps(migration_signals, indent=2)}

Return strict JSON only in this shape:
{{
  "governance_assessment": {{
    "risk_level": "Low|Medium|High",
    "issues": [],
    "passed_checks": [],
    "recommendations": [],
    "recommendation": ""
  }},
  "modernization_opportunities": [],
  "migration_roadmap": []
}}

Rules:
- Make the output specific to the detected stack, selected provider, strategy, and user requirements.
- Use the derived planning profile as the source of truth for sizing, traffic posture, budget posture, delivery timeline, and risk posture.
- Make Low, Medium, and High traffic produce visibly different validation and capacity planning steps.
- Make Immediate, 3 Months, 6 Months, and Flexible timelines produce visibly different sequencing, governance, and validation depth.
- Make Low Cost, Balanced, and Performance Focused budgets produce visibly different modernization and governance recommendations.
- When the same repository is assessed with different selected fields, roadmap and governance must show realistic differences caused by those fields.
- Timeline should not invent different runtime costs, but it should change delivery sequencing, review depth, cutover risk, and validation scope.
- Budget should change cost-control and tier-selection guidance.
- Traffic should change scaling, observability, and testing guidance.
- Keep each list item concise and action-oriented.
- Include 3-7 modernization opportunities.
- Include 10-14 detailed roadmap steps in execution order.
- Roadmap must cover the full application migration lifecycle: discovery, dependency inventory, target architecture, landing zone/IAM/networking, runtime or container preparation, database/data migration, configuration and secrets, cloud service integration, CI/CD and infrastructure automation, testing, cutover and rollback, observability, and post-migration optimization.
- Each roadmap item should name the detected application stack or dependency where relevant.
- Generate fresh security, modernization, and roadmap language from the evidence signals.
- Keep factual findings grounded in repository facts. If something is absent, phrase it as not detected.
- Do not claim a vulnerability exists unless it appears in governance_findings_from_repository.
- Do not use markdown.
"""

    raw = _chat_completion(
        [
            {
                "role": "system",
                "content": "You return strict JSON only. No markdown. No commentary.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        fallback="{}",
        temperature=0.35,
        max_tokens=2600,
        response_format={"type": "json_object"},
        label="migration-guidance",
    )

    try:
        data = _load_json_object(raw)
        if not data:
            warnings.append(
                "LLM migration guidance returned an empty response. Using rule-based guidance."
            )
            return fallback_governance, fallback_opportunities, fallback_roadmap, warnings

        governance_data = data.get("governance_assessment") or {}
        opportunities = _string_list(data.get("modernization_opportunities"))
        roadmap = _string_list(data.get("migration_roadmap"))

        governance = GovernanceAssessment.model_validate(
            {
                **fallback_governance.model_dump(),
                **governance_data,
            }
        )

        if not opportunities:
            warnings.append(
                "LLM migration guidance did not return modernization opportunities. Using rule-based opportunities."
            )
            opportunities = fallback_opportunities

        if not roadmap:
            warnings.append(
                "LLM migration guidance did not return a migration roadmap. Using rule-based roadmap."
            )
            roadmap = fallback_roadmap

        return governance, opportunities, roadmap, warnings

    except Exception as exc:
        warnings.append(
            f"LLM migration guidance failed: {exc}. Raw response preview: {_safe_preview(raw)}"
        )
        return fallback_governance, fallback_opportunities, fallback_roadmap, warnings


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
        label="aws-pricing",
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
        label="chat",
    )


def _chat_completion(
    messages: list[dict[str, str]],
    fallback: str,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, str] | None,
    label: str = "chat",
) -> str:
    api_keys = _groq_api_keys()
    if not api_keys:
        return fallback

    payload = {
        "model": groq_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    for index, api_key in enumerate(api_keys, start=1):
        key_label = "primary" if index == 1 else f"fallback-{index}"

        print(
            "Calling Groq:",
            f"label={label}",
            f"key={key_label}",
            f"model={payload.get('model')}",
            f"endpoint={GROQ_ENDPOINT}",
        )

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
                if not content:
                    print(
                        "Groq returned an empty message content.",
                        f"label={label}",
                        f"key={key_label}",
                        f"model={payload.get('model')}",
                        f"endpoint={GROQ_ENDPOINT}",
                    )
                    continue

                print(
                    "Groq response received:",
                    f"label={label}",
                    f"key={key_label}",
                    f"chars={len(content)}",
                    f"preview={_safe_preview(content)}",
                )
                return content
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text if exc.response is not None else ""
            print(
                "Groq API request failed:",
                f"label={label}",
                f"key={key_label}",
                f"status={exc.response.status_code if exc.response is not None else 'unknown'}",
                f"model={payload.get('model')}",
                f"endpoint={GROQ_ENDPOINT}",
                f"response={_safe_preview(response_text)}",
            )
        except Exception as exc:
            print(
                "Groq API request failed:",
                f"label={label}",
                f"key={key_label}",
                f"type={type(exc).__name__}",
                f"model={payload.get('model')}",
                f"endpoint={GROQ_ENDPOINT}",
                f"error={exc}",
            )

    print(
        "All configured Groq keys failed. Returning fallback.",
        f"label={label}",
        f"configured_keys={len(api_keys)}",
    )
    return fallback


def _groq_api_keys() -> list[str]:
    keys: list[str] = []
    for api_key in (GROQ_API_KEY, GROQ_API_KEY_2):
        if api_key and api_key not in keys:
            keys.append(api_key)
    return keys


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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


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
