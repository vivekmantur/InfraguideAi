from __future__ import annotations
from dataclasses import dataclass
from uuid import uuid4
from ..ai import (
    generate_architect_reasoning,
    generate_migration_guidance,
    generate_service_recommendations,
)
from ..migration_strategy import determine_migration_strategy, assess_strategy_alignment
from .mcp_client import (
    CloudMcpClient
)
from ..models import (
    AssessmentRequest,
    AssessmentResponse,
    CostEstimate,
    FolderAssessmentRequest,
    GovernanceAssessment,
    ReadinessAssessment,
    RepositoryAnalysis,
    ServiceRecommendation,
    CloudSizingRequirements
)
from ..storage import utc_now

@dataclass(frozen=True)
class RequirementsProfile:
    """Normalized migration requirements used to tune sizing, risk, and services."""

    cpu_cores: int
    memory_gb: int
    storage_gb: int
    traffic_label: str
    budget_label: str
    goal_label: str
    timeline_label: str
    traffic_multiplier: float
    budget_multiplier: float
    risk_modifier: int
    service_posture: str
    timeline_posture: str
    sizing_reason: str

SERVICE_MAP = {
    "Azure": {
        "container": "Azure Container Apps",
        "function": "Azure Functions Premium Plan",
        "database": "Azure SQL Database / Azure Database for PostgreSQL",
        "storage": "Azure Blob Storage",
        "secrets": "Azure Key Vault",
        "monitoring": "Azure Monitor",
        "data_integration": "Azure Data Factory",
        "queue": "Azure Service Bus",
        "streaming": "Azure Event Hubs",
        "registry": "Azure Container Registry",
        "api_gateway": "Azure API Management",
        "cdn_waf": "Azure Front Door with Web Application Firewall",
    },
    "AWS": {
        "container": "Amazon ECS Fargate",
        "function": "AWS Lambda",
        "database": "Amazon RDS",
        "storage": "Amazon S3",
        "secrets": "AWS Secrets Manager",
        "monitoring": "Amazon CloudWatch",
        "data_integration": "AWS Glue",
        "queue": "Amazon SQS",
        "streaming": "Amazon Kinesis",
        "registry": "Amazon ECR",
        "api_gateway": "Amazon API Gateway",
        "cdn_waf": "Amazon CloudFront with AWS WAF",
    },
    "GCP": {
        "container": "Cloud Run",
        "function": "Cloud Functions",
        "database": "Cloud SQL",
        "storage": "Cloud Storage",
        "secrets": "Secret Manager",
        "monitoring": "Cloud Monitoring",
        "data_integration": "Cloud Data Fusion",
        "queue": "Pub/Sub",
        "streaming": "Pub/Sub",
        "registry": "Artifact Registry",
        "api_gateway": "API Gateway",
        "cdn_waf": "Cloud CDN with Cloud Armor",
    },
}

async def build_assessment(request: AssessmentRequest | FolderAssessmentRequest, analysis: RepositoryAnalysis, warnings: list[str]) -> AssessmentResponse:
    """Build the complete migration assessment response from repository analysis.

    Args:
        request: GitHub or uploaded-folder assessment request.
        analysis: Repository analysis generated from source evidence.
        warnings: Warnings accumulated during analysis.

    Returns:
        Complete assessment response ready for the frontend.
    """
    requirements_profile = _requirements_profile(
        request,
        analysis
    )
    strategy_result = determine_migration_strategy(
    request.requirements.migration_goal,
    analysis
    )
    strategy_assessment = assess_strategy_alignment(
    request.requirements.migration_goal,
    strategy_result
)
    provider = _select_provider(request, analysis)
    readiness = _readiness(analysis)
    fallback_services = _services(
        provider,
        analysis,
        request,
        requirements_profile
    )
    services, service_warnings = generate_service_recommendations(
        analysis,
        request.requirements,
        provider,
        strategy_result,
        fallback_services,
        _requirements_profile_payload(requirements_profile),
    )
    warnings.extend(service_warnings)
    services = _apply_requirement_service_adjustments(
        provider,
        analysis,
        request,
        services
    )
    cost = await _cost_estimate(
        request,
        analysis,
        services,
        requirements_profile
    )
    fallback_opportunities = _modernization_opportunities(
        analysis,
        provider,
        request,
        requirements_profile
    )
    strategy = strategy_result.strategy
    fallback_roadmap = _roadmap(
        strategy,
        analysis,
        provider,
        request,
        requirements_profile
    )
    architecture_summary = _architecture_summary(analysis)
    fallback_governance = _governance(
        analysis,
        provider,
        request,
        requirements_profile
    )
    governance, opportunities, roadmap, guidance_warnings = generate_migration_guidance(
        analysis,
        request.requirements,
        provider,
        strategy_result,
        [item.model_dump() for item in services],
        fallback_governance,
        fallback_opportunities,
        fallback_roadmap,
        _requirements_profile_payload(requirements_profile),
    )
    warnings.extend(guidance_warnings)
    opportunities = _apply_requirement_opportunities(
        opportunities,
        request,
        requirements_profile
    )
    roadmap = _apply_requirement_roadmap(
        roadmap,
        request,
        requirements_profile
    )
    governance = _apply_requirement_governance(
        governance,
        request,
        requirements_profile
    )
    ai_reasoning = generate_architect_reasoning(
        analysis,
        provider,
        [item.model_dump() for item in services],
        cost.model_dump(),
        roadmap,
        strategy_result,
        _requirements_profile_payload(requirements_profile),
    )
    cloud_sizing = cloud_sizing = (
        analysis.cloud_sizing
        if analysis.cloud_sizing
        else CloudSizingRequirements()
    )

    response = AssessmentResponse(
        id=str(uuid4()),
        created_at=utc_now(),
        technology_stack=analysis,
        architecture_summary=architecture_summary,
        cloud_readiness=readiness,
        recommended_provider=provider,
        recommended_services=services,
        cost_estimation=cost,
        modernization_opportunities=opportunities,
        migration_strategy=strategy,
        migration_roadmap=roadmap,
        governance_assessment=governance,
        ai_reasoning=ai_reasoning,
        blueprint_markdown="",
        warnings=_user_visible_warnings(warnings),
        cloud_sizing=cloud_sizing,
        strategy_assessment=strategy_assessment,
    )
    response.blueprint_markdown = render_blueprint(response)
    return response

def render_blueprint(assessment: AssessmentResponse) -> str:
    """Render a migration assessment as Markdown blueprint text.

    Args:
        assessment: Complete migration assessment response.

    Returns:
        Markdown-formatted migration blueprint.
    """
    services = "\n".join(
        f"- {item.component}: {item.current} -> {item.recommended}"
        for item in assessment.recommended_services
    )
    opportunities = "\n".join(f"- {item}" for item in assessment.modernization_opportunities)
    roadmap = "\n".join(f"{index}. {item}" for index, item in enumerate(assessment.migration_roadmap, start=1))
    warnings = "\n".join(f"- {item}" for item in assessment.warnings) or "- None"

    stack = assessment.technology_stack

    strategy_assessment = assessment.strategy_assessment

    strategy_section = ""

    strategy_section = f"""
## 8. Migration Strategy Assessment

- Given Migration Strategy: {strategy_assessment.user_goal}
- Infraguide Recommended Migration Strategy: {strategy_assessment.recommended_strategy}
- Confidence: {strategy_assessment.confidence}
"""
    return f"""# InfraGuide AI Migration Blueprint

## 1. Technology Stack Analysis

- Languages: {_join(stack.languages)}
- Frameworks: {_join(stack.frameworks)}
- Runtime: {_join(stack.runtimes)}
- Hosting Model: {stack.hosting_model}
- Deployment Model: {stack.deployment_model}
- Triggers: {_join(stack.triggers)}
- Databases: {_join(stack.databases)}
- Package Managers: {_join(stack.package_managers)}
- Container Configurations: {_join(stack.container_configs)}
- Infrastructure Configurations: {_join(stack.infrastructure_configs)}
- CI/CD Configurations: {_join(stack.cicd_configs)}
- External Dependencies: {_join(stack.external_dependencies)}
- Cloud Dependencies: {_join(stack.cloud_dependencies)}

Project Summary:
{stack.project_summary}

Dependency Graph:
{_bullet_list(stack.dependency_graph)}

## 2. Application Architecture Summary

{assessment.architecture_summary}

## 3. Cloud Readiness Assessment

- Score: {assessment.cloud_readiness.score}%
- Complexity: {assessment.cloud_readiness.complexity}
- Runtime Compatibility: {assessment.cloud_readiness.runtime_compatibility}
- Database Compatibility: {assessment.cloud_readiness.database_compatibility}
- Container Readiness: {assessment.cloud_readiness.container_readiness}
- Configuration Readiness: {assessment.cloud_readiness.configuration_readiness}

Score Breakdown:
{_bullet_list(assessment.cloud_readiness.score_breakdown)}

## 4. Cloud Provider Recommendation

{assessment.recommended_provider}

## 5. Recommended Cloud Services

{services}

## 6. Cost Estimation

- Monthly Cost: INR {assessment.cost_estimation.monthly:,}
- Monthly Range: {assessment.cost_estimation.monthly_range}
- Annual Cost: INR {assessment.cost_estimation.annual:,}

Line Items:
{_bullet_list(assessment.cost_estimation.line_items)}

Assumptions:
{_bullet_list(assessment.cost_estimation.assumptions)}

## 7. Modernization Opportunities

{opportunities}

{strategy_section}

## 9. Migration Roadmap

{roadmap}

## 10. Security and Governance

- Risk Level: {assessment.governance_assessment.risk_level}
- Recommendation: {assessment.governance_assessment.recommendation}

Issues:
{_bullet_list(assessment.governance_assessment.issues)}

Passed Checks:
{_bullet_list(assessment.governance_assessment.passed_checks)}

Recommendations:
{_bullet_list(assessment.governance_assessment.recommendations)}

## 11. AI Architect Reasoning

{assessment.ai_reasoning}

## 12. Approval Status

{assessment.approval_status.value}

## 13. Analysis Warnings

{warnings}
"""

def _select_provider(request: AssessmentRequest | FolderAssessmentRequest, analysis: RepositoryAnalysis) -> str:
    """Select the target cloud provider from explicit preference and stack hints.

    Args:
        request: Assessment request containing cloud preference.
        analysis: Repository analysis used when no preference is selected.

    Returns:
        Selected provider name.
    """
    if request.requirements.cloud_provider.value != "No Preference":
        return request.requirements.cloud_provider.value
    if "Azure Functions" in analysis.frameworks or "ASP.NET Core" in analysis.frameworks or "SQL Server" in analysis.databases:
        return "Azure"
    if request.requirements.budget_preference.value == "Low Cost":
        return "GCP"
    return "AWS"

def _requirements_profile(
    request: AssessmentRequest | FolderAssessmentRequest,
    analysis: RepositoryAnalysis
) -> RequirementsProfile:
    """Translate user requirements and detected sizing into a planning profile.

    Args:
        request: Assessment request containing migration requirements.
        analysis: Repository analysis with optional detected cloud sizing.

    Returns:
        Normalized requirements profile for sizing, pricing, and guidance.
    """
    detected = analysis.cloud_sizing
    traffic = request.requirements.expected_traffic.value
    budget = request.requirements.budget_preference.value
    goal = request.requirements.migration_goal.value
    timeline = request.requirements.migration_timeline.value

    traffic_sizing = {
        "Low": (1, 2, 0.85, "small workload baseline for low expected traffic"),
        "Medium": (2, 4, 1.0, "standard production baseline for medium expected traffic"),
        "High": (4, 8, 1.55, "scaled production baseline for high expected traffic"),
    }
    min_cpu, min_memory, traffic_multiplier, sizing_reason = traffic_sizing.get(
        traffic,
        traffic_sizing["Medium"]
    )

    budget_multipliers = {
        "Low Cost": 0.85,
        "Balanced": 1.0,
        "Performance Focused": 1.35,
    }
    budget_multiplier = budget_multipliers.get(
        budget,
        1.0
    )

    if budget == "Performance Focused":
        min_cpu = max(min_cpu, 4)
        min_memory = max(min_memory, 8)
        service_posture = "performance-focused"
    elif budget == "Low Cost":
        service_posture = "cost-optimized"
    else:
        service_posture = "balanced"

    if goal in {"Scalability", "Performance Improvement"}:
        min_cpu = max(min_cpu, 2)
        min_memory = max(min_memory, 4)
    if goal == "Performance Improvement":
        min_cpu = max(min_cpu, 4)
        min_memory = max(min_memory, 8)

    timeline_posture = {
        "Immediate": "compressed delivery with reduced change scope",
        "3 Months": "phased delivery with standard validation",
        "6 Months": "extended delivery with deeper testing and optimization",
        "Flexible": "modernization-led delivery with broader hardening",
    }.get(
        timeline,
        "phased delivery with standard validation"
    )

    risk_modifier = {
        "Immediate": 1,
        "3 Months": 0,
        "6 Months": -1,
        "Flexible": -1,
    }.get(
        timeline,
        0
    )

    return RequirementsProfile(
        cpu_cores=max(detected.cpu_cores, min_cpu) if detected else min_cpu,
        memory_gb=max(detected.memory_gb, min_memory) if detected else min_memory,
        storage_gb=max(detected.storage_gb, 25 if traffic == "Low" else 50 if traffic == "Medium" else 100) if detected else 25 if traffic == "Low" else 50 if traffic == "Medium" else 100,
        traffic_label=traffic,
        budget_label=budget,
        goal_label=goal,
        timeline_label=timeline,
        traffic_multiplier=traffic_multiplier,
        budget_multiplier=budget_multiplier,
        risk_modifier=risk_modifier,
        service_posture=service_posture,
        timeline_posture=timeline_posture,
        sizing_reason=sizing_reason,
    )

def _requirements_profile_payload(
    profile: RequirementsProfile
) -> dict:
    """Convert a requirements profile into JSON-serializable prompt context.

    Args:
        profile: Normalized requirements profile.

    Returns:
        Dictionary payload safe to include in LLM prompts.
    """
    return {
        "cpu_cores": profile.cpu_cores,
        "memory_gb": profile.memory_gb,
        "storage_gb": profile.storage_gb,
        "traffic_label": profile.traffic_label,
        "budget_label": profile.budget_label,
        "goal_label": profile.goal_label,
        "timeline_label": profile.timeline_label,
        "traffic_multiplier": profile.traffic_multiplier,
        "budget_multiplier": profile.budget_multiplier,
        "service_posture": profile.service_posture,
        "timeline_posture": profile.timeline_posture,
        "sizing_reason": profile.sizing_reason,
    }

def _pricing_adjustment_lines(
    profile: RequirementsProfile
) -> list[str]:
    """Describe cost changes caused by traffic and budget preferences.

    Args:
        profile: Normalized requirements profile.

    Returns:
        Human-readable pricing adjustment lines.
    """
    lines: list[str] = []

    if profile.traffic_multiplier != 1:
        lines.append(
            (
                f"Traffic adjustment: {profile.traffic_label} traffic "
                f"{_multiplier_effect(profile.traffic_multiplier)} "
                f"({profile.sizing_reason})."
            )
        )

    if profile.budget_multiplier != 1:
        lines.append(
            (
                f"Budget adjustment: {profile.budget_label} "
                f"{_multiplier_effect(profile.budget_multiplier)} "
                f"({profile.service_posture})."
            )
        )

    return lines

def _multiplier_effect(
    multiplier: float
) -> str:
    """Convert a numeric pricing multiplier into a readable effect phrase.

    Args:
        multiplier: Pricing multiplier relative to baseline.

    Returns:
        Text describing the estimated percentage increase or reduction.
    """
    percentage = round(
        abs(
            1 - multiplier
        )
        * 100
    )

    if multiplier < 1:
        return f"reduces estimate by {percentage}%"

    return f"increases estimate by {percentage}%"

def _readiness(analysis: RepositoryAnalysis) -> ReadinessAssessment:
    """Calculate cloud readiness score and detailed scoring findings.

    Args:
        analysis: Repository analysis containing stack and deployment signals.

    Returns:
        Cloud readiness assessment with score, complexity, and findings.
    """
    score = 40
    findings: list[str] = []
    breakdown: list[str] = ["Base repository analyzability: +40"]

    if analysis.runtimes:
        score += 15
        runtime = "Ready"
        breakdown.append(f"Cloud compatible runtime detected ({_join(analysis.runtimes)}): +15")
    else:
        runtime = "Needs Review"
        findings.append("Runtime stack was not clearly detected.")
        breakdown.append("Runtime stack not clearly detected: +0")

    if analysis.frameworks:
        score += 10
        breakdown.append(f"Application framework detected ({_join(analysis.frameworks)}): +10")
    else:
        findings.append("Application framework was not clearly detected.")

    if analysis.databases:
        score += 10
        database = "Needs Migration"
        breakdown.append(f"Persistent database dependency detected ({_join(analysis.databases)}): +10")
    else:
        database = "Ready"
        findings.append("No persistent database dependency was detected.")
        breakdown.append("No database migration dependency detected: +10")
        score += 10

    if "Azure Functions" in analysis.frameworks:
        score += 15
        container = "Not Required for Serverless"
        breakdown.append("Serverless hosting model already detected: +15")
    elif analysis.container_configs:
        score += 15
        container = "Ready"
        breakdown.append("Container configuration detected: +15")
    else:
        container = "Requires Containerization"
        findings.append("No Docker configuration was detected.")
        breakdown.append("No container or serverless deployment model detected: +0")

    if analysis.package_managers:
        score += 5
        config = "Good"
        breakdown.append(f"Package manager metadata detected ({_join(analysis.package_managers)}): +5")
    else:
        config = "Needs Improvement"
        findings.append("Package manager metadata was not detected.")
        breakdown.append("Package manager metadata not detected: +0")

    if analysis.governance_findings:
        penalty = min(15, len(analysis.governance_findings) * 5)
        score -= penalty
        breakdown.append(f"Security/governance findings penalty: -{penalty}")
    else:
        breakdown.append("No high-risk static security findings detected: +0 penalty")

    score = min(score, 100)
    complexity = "Low" if score >= 85 else "Medium" if score >= 65 else "High"

    return ReadinessAssessment(
        runtime_compatibility=runtime,
        database_compatibility=database,
        container_readiness=container,
        configuration_readiness=config,
        score=score,
        complexity=complexity,
        findings=findings,
        score_breakdown=breakdown,
    )

def _services(
    provider: str,
    analysis: RepositoryAnalysis,
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> list[ServiceRecommendation]:
    """Create deterministic provider service recommendations from detected signals.

    Args:
        provider: Selected cloud provider.
        analysis: Repository analysis containing stack and dependency signals.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Provider-specific service recommendations.
    """
    cloud = SERVICE_MAP[provider]
    if request.requirements.migration_goal.value == "Lift-and-Shift":
        runtime_recommendation = (
            "Amazon EC2"
            if provider == "AWS"
            else "Azure Virtual Machines"
            if provider == "Azure"
            else "Compute Engine"
        )
    elif (
        request.requirements.migration_goal.value == "Cost Optimization"
        and request.requirements.expected_traffic.value == "Low"
    ):
        runtime_recommendation = cloud["function"]
    else:
        runtime_recommendation = cloud["function"] if "Azure Functions" in analysis.frameworks else cloud["container"]
    current_runtime = analysis.deployment_model if analysis.deployment_model != "Unknown" else _join(analysis.frameworks or analysis.runtimes)
    storage_signals = [item for item in analysis.cloud_dependencies if "Storage" in item]
    services = [
        ServiceRecommendation(component="Application Runtime", current=current_runtime, recommended=runtime_recommendation),
        ServiceRecommendation(component="File Storage", current=_join(analysis.storage_dependencies or storage_signals) if analysis.storage_dependencies or storage_signals else "Local or application-managed storage", recommended=cloud["storage"]),
        ServiceRecommendation(component="Secrets", current="Configuration files or environment variables", recommended=cloud["secrets"]),
        ServiceRecommendation(component="Monitoring", current="Application logs", recommended=cloud["monitoring"]),
    ]
    if analysis.databases:
        services.insert(
            1,
            ServiceRecommendation(component="Database", current=_join(analysis.databases), recommended=cloud["database"]),
        )
    if _has_dependency_signal(analysis, ["data factory", "datafactory", "etl", "data pipeline"]):
        services.append(
            ServiceRecommendation(component="Data Integration", current=_matched_dependency(analysis, ["Data Factory", "ETL", "data pipeline"]), recommended=cloud["data_integration"])
        )
    if _has_dependency_signal(analysis, ["service bus", "queue", "sqs", "pub/sub"]):
        services.append(
            ServiceRecommendation(component="Messaging", current=_matched_dependency(analysis, ["Service Bus", "queue", "Pub/Sub"]), recommended=cloud["queue"])
        )
    if _has_dependency_signal(analysis, ["event hub", "eventhub", "kinesis", "streaming"]):
        services.append(
            ServiceRecommendation(component="Event Streaming", current=_matched_dependency(analysis, ["Event Hubs", "streaming"]), recommended=cloud["streaming"])
        )
    if analysis.container_configs:
        services.append(
            ServiceRecommendation(component="Container Registry", current=_join(analysis.container_configs), recommended=cloud["registry"])
        )
    if "HTTP" in analysis.triggers and analysis.application_type == "Web Application":
        services.append(
            ServiceRecommendation(component="API Gateway", current="HTTP application endpoint", recommended=cloud["api_gateway"])
        )
    if request_public_edge(analysis) or request.requirements.expected_traffic.value == "High":
        services.append(
            ServiceRecommendation(component="Edge Security", current="Public web traffic", recommended=cloud["cdn_waf"])
        )
    if request.requirements.expected_traffic.value == "High" or request.requirements.migration_goal.value in {"Scalability", "Performance Improvement"}:
        services.append(
            ServiceRecommendation(component="Autoscaling", current="Manual or not detected", recommended=f"{runtime_recommendation} autoscaling policy")
        )
    if request.requirements.budget_preference.value == "Performance Focused":
        services.append(
            ServiceRecommendation(component="Performance Monitoring", current="Basic application logs", recommended=f"{cloud['monitoring']} performance dashboards and alert rules")
        )
    return services

def _has_dependency_signal(analysis: RepositoryAnalysis, signals: list[str]) -> bool:
    """Return whether repository dependency evidence contains any requested signal.

    Args:
        analysis: Repository analysis containing dependency evidence.
        signals: Text signals to search for.

    Returns:
        True when any signal appears in dependency evidence; otherwise False.
    """
    haystack = " ".join(
        [
            *analysis.cloud_dependencies,
            *analysis.external_dependencies,
            *analysis.dependency_graph,
            *analysis.infrastructure_configs,
            *analysis.frameworks,
        ]
    ).lower()
    return any(signal.lower() in haystack for signal in signals)

def _matched_dependency(analysis: RepositoryAnalysis, labels: list[str]) -> str:
    """Return the first detected dependency that matches the provided labels.

    Args:
        analysis: Repository analysis containing detected dependencies.
        labels: Dependency labels to match.

    Returns:
        Matching dependency name, or the first label when none is detected.
    """
    dependencies = [*analysis.cloud_dependencies, *analysis.external_dependencies]
    for label in labels:
        for dependency in dependencies:
            if label.lower() in dependency.lower():
                return dependency
    return labels[0]

def request_public_edge(analysis: RepositoryAnalysis) -> bool:
    """Return whether the app appears to need a public edge protection layer.

    Args:
        analysis: Repository analysis containing trigger and framework signals.

    Returns:
        True when the application appears public HTTP-facing; otherwise False.
    """
    return "HTTP" in analysis.triggers and any(
        item in analysis.frameworks
        for item in ["React", "Next.js", "ASP.NET Core MVC"]
    )

def _apply_requirement_service_adjustments(
    provider: str,
    analysis: RepositoryAnalysis,
    request: AssessmentRequest | FolderAssessmentRequest,
    services: list[ServiceRecommendation]
) -> list[ServiceRecommendation]:
    """Add or reshape service recommendations based on selected requirements.

    Args:
        provider: Selected cloud provider.
        analysis: Repository analysis containing stack and dependency signals.
        request: Assessment request containing migration requirements.
        services: Existing service recommendations.

    Returns:
        Deduplicated service recommendations after requirement adjustments.
    """
    adjusted = list(services)
    components = {
        service.component.lower()
        for service in adjusted
    }
    cloud = SERVICE_MAP[provider]

    if (
        request.requirements.expected_traffic.value == "High"
        or request.requirements.migration_goal.value in {"Scalability", "Performance Improvement"}
    ) and "autoscaling" not in components:
        runtime = next(
            (
                service.recommended
                for service in adjusted
                if service.component.lower() == "application runtime"
            ),
            cloud["container"]
        )
        adjusted.append(
            ServiceRecommendation(
                component="Autoscaling",
                current="Manual or not detected",
                recommended=f"{runtime} autoscaling policy"
            )
        )

    if (
        request.requirements.expected_traffic.value == "High"
        and "edge security" not in components
        and ("HTTP" in analysis.triggers or analysis.application_type == "Web Application")
    ):
        adjusted.append(
            ServiceRecommendation(
                component="Edge Security",
                current="Public web traffic",
                recommended=cloud["cdn_waf"]
            )
        )

    if (
        request.requirements.budget_preference.value == "Performance Focused"
        and "performance monitoring" not in components
    ):
        adjusted.append(
            ServiceRecommendation(
                component="Performance Monitoring",
                current="Basic application logs",
                recommended=f"{cloud['monitoring']} performance dashboards and alert rules"
            )
        )

    if (
        request.requirements.migration_goal.value == "Cost Optimization"
        and "cost controls" not in components
    ):
        adjusted.append(
            ServiceRecommendation(
                component="Cost Controls",
                current="Not detected",
                recommended=f"{provider} budgets, tagging, and rightsizing recommendations"
            )
        )

    return _dedupe_services(adjusted)[:10]

async def _cost_estimate(
    request: AssessmentRequest | FolderAssessmentRequest,
    analysis: RepositoryAnalysis,
    services: list[ServiceRecommendation] | None = None,
    profile: RequirementsProfile | None = None
) -> CostEstimate:
    """Estimate monthly runtime and managed service costs for the assessment.

    Args:
        request: Assessment request containing provider and migration requirements.
        analysis: Repository analysis containing sizing and dependency signals.
        services: Optional service recommendations to price.
        profile: Optional normalized requirements profile.

    Returns:
        Cost estimate with monthly, annual, assumptions, and regional prices.
    """

    provider = _select_provider(
        request,
        analysis
    )
    profile = profile or _requirements_profile(
        request,
        analysis
    )

    if provider in {"GCP", "Azure"}:

        cloud_sizing = CloudSizingRequirements(
            cpu_cores=profile.cpu_cores,
            memory_gb=profile.memory_gb,
            storage_gb=profile.storage_gb,
            confidence="Medium",
        )

        cpu = cloud_sizing.cpu_cores
        memory = cloud_sizing.memory_gb

        mcp_client = CloudMcpClient()

        if provider == "GCP":

            try:

                pricing = await mcp_client.get_gcp_compute_pricing(
                    cpu=cpu,
                    memory=memory
                )

            except Exception as ex:

                pricing = {
                    "error": str(ex)
                }

            if pricing is None:
                pass

            elif (
                isinstance(pricing, dict)
                and "error" not in pricing
            ):

                monthly = pricing["monthly_cost"]
                service_pricing = None
                additional_monthly = 0
                additional_line_items: list[str] = []
                additional_assumptions: list[str] = []
                regional_prices: list[dict] = []
                billable_services: list[ServiceRecommendation] = []

                if services:

                    billable_services = [
                        service
                        for service in services
                        if service.component != "Application Runtime"
                    ]

                    try:

                        service_pricing = await mcp_client.get_gcp_service_pricing(
                            services=[
                                service.model_dump()
                                for service in billable_services
                            ]
                        )

                    except Exception as ex:
                        service_pricing = {
                            "error": str(ex)
                        }

                    if (
                        isinstance(service_pricing, dict)
                        and "error" not in service_pricing
                    ):

                        additional_monthly = int(
                            service_pricing.get(
                                "monthly_cost",
                                0
                            )
                        )
                        additional_line_items.extend(
                            service_pricing.get(
                                "line_items",
                                []
                            )
                        )
                        additional_assumptions.extend(
                            service_pricing.get(
                                "assumptions",
                                []
                            )
                        )

                total_monthly = (monthly + additional_monthly) * profile.traffic_multiplier * profile.budget_multiplier

                lower = int(total_monthly * 0.9)
                upper = int(total_monthly * 1.1)

                return CostEstimate(
                    currency=pricing.get(
                        "currency",
                        "USD"
                    ),
                    monthly=int(total_monthly),
                    monthly_range=(
                        f"{pricing.get('currency', 'USD')} "
                        f"{lower:,} - {upper:,}/month"
                    ),
                    annual=int(total_monthly * 12),
                    line_items=[
                        (
                            f"GCP Compute Engine "
                            f"({pricing['machine_type']})"
                        ),
                        f"{cpu} vCPU",
                        f"{memory} GB RAM",
                        (
                            "Pricing retrieved from "
                            "Google Cloud Billing API"
                        ),
                        f"Traffic profile adjustment: {profile.traffic_label} ({profile.sizing_reason})",
                        f"Budget posture: {profile.budget_label} ({profile.service_posture})",
                    ] + additional_line_items,
                    assumptions=[
                        (
                            f"Machine type selected: "
                            f"{pricing['machine_type']}"
                        ),
                        f"CPU requirement: {cpu}",
                        f"Memory requirement: {memory}",
                        f"Migration goal: {profile.goal_label}",
                        f"Migration timeline: {profile.timeline_label} ({profile.timeline_posture})",
                        (
                            "Cost calculated using "
                            "Google Cloud Billing API"
                        )
                    ] + additional_assumptions,
                    regional_prices=regional_prices,
                )

        elif provider == "Azure":

            try:

                pricing = await mcp_client.get_azure_vm_pricing(
                    cpu=cpu,
                    memory=memory
                )

            except Exception as ex:

                pricing = {
                    "error": str(ex)
                }

            if pricing is None:
                pass

            elif (
                isinstance(pricing, dict)
                and "error" not in pricing
            ):

                monthly = pricing["monthly_cost"]
                service_pricing = None
                additional_monthly = 0
                additional_line_items: list[str] = []
                additional_assumptions: list[str] = []
                regional_prices: list[dict] = []
                billable_services: list[ServiceRecommendation] = []

                if services:

                    billable_services = [
                        service
                        for service in services
                        if service.component != "Application Runtime"
                    ]

                    try:

                        service_pricing = await mcp_client.get_azure_service_pricing(
                            services=[
                                service.model_dump()
                                for service in billable_services
                            ],
                            region=pricing.get(
                                "region",
                                "eastus"
                            )
                        )

                    except Exception as ex:
                        service_pricing = {
                            "error": str(ex)
                        }

                    if (
                        isinstance(service_pricing, dict)
                        and "error" not in service_pricing
                    ):

                        additional_monthly = int(
                            service_pricing.get(
                                "monthly_cost",
                                0
                            )
                        )
                        additional_line_items.extend(
                            service_pricing.get(
                                "line_items",
                                []
                            )
                        )
                        additional_assumptions.extend(
                            service_pricing.get(
                                "assumptions",
                                []
                            )
                        )

                total_monthly = (monthly + additional_monthly) * profile.traffic_multiplier * profile.budget_multiplier

                lower = int(total_monthly * 0.9)
                upper = int(total_monthly * 1.1)

                return CostEstimate(
                    currency=pricing.get(
                        "currency",
                        "USD"
                    ),
                    monthly=int(total_monthly),
                    monthly_range=(
                        f"{pricing.get('currency', 'USD')} "
                        f"{lower:,} - {upper:,}/month"
                    ),
                    annual=int(total_monthly * 12),
                    line_items=[
                        (
                            f"Azure VM "
                            f"({pricing['sku']})"
                        ),
                        f"{cpu} vCPU",
                        f"{memory} GB RAM",
                        (
                            "Pricing retrieved from "
                            "Azure Retail Pricing API"
                        ),
                        f"Traffic profile adjustment: {profile.traffic_label} ({profile.sizing_reason})",
                        f"Budget posture: {profile.budget_label} ({profile.service_posture})",
                    ] + additional_line_items,
                    assumptions=[
                        (
                            f"VM SKU selected: "
                            f"{pricing['sku']}"
                        ),
                        (
                            f"Azure region: "
                            f"{pricing['region']}"
                        ),
                        f"CPU requirement: {cpu}",
                        f"Memory requirement: {memory}",
                        f"Migration goal: {profile.goal_label}",
                        f"Migration timeline: {profile.timeline_label} ({profile.timeline_posture})",
                        (
                            "Cost calculated using "
                            "Azure Retail Pricing API"
                        )
                    ] + additional_assumptions,
                    regional_prices=regional_prices,
                )

    if provider == "AWS":

        cloud_sizing = CloudSizingRequirements(
            cpu_cores=profile.cpu_cores,
            memory_gb=profile.memory_gb,
            storage_gb=profile.storage_gb,
            confidence="Medium",
        )

        try:
            mcp_client = CloudMcpClient()
            pricing_data = await mcp_client.get_aws_regional_pricing(
                cpu=cloud_sizing.cpu_cores,
                memory=cloud_sizing.memory_gb,
                services=[
                    service.model_dump()
                    for service in (services or [])
                ],
                limit=10,
            )
        except Exception as exc:
            pricing_data = None

        if pricing_data:
            regional_prices = [
                row
                for row in pricing_data.get(
                    "regions",
                    []
                )
                if isinstance(
                    row,
                    dict
                )
                and row.get(
                    "region"
                )
                and row.get(
                    "total_monthly"
                ) is not None
            ]

            if regional_prices:

                regional_prices = sorted(
                    regional_prices,
                    key=lambda item: item.get(
                        "total_monthly",
                        0
                    )
                )
                primary_region = regional_prices[0]
                currency = pricing_data.get(
                    "currency",
                    primary_region.get(
                        "currency",
                        "USD"
                    )
                )
                totals = [
                    float(
                        item.get(
                            "total_monthly",
                            0
                        )
                    )
                    for item in regional_prices
                ]
                monthly = int(
                    round(
                        float(
                            primary_region.get(
                            "total_monthly",
                            0
                            )
                        )
                        * profile.traffic_multiplier
                        * profile.budget_multiplier
                    )
                )
                annual = int(
                    monthly * 12
                )
                lower = int(
                    round(
                        min(totals)
                        * profile.traffic_multiplier
                        * profile.budget_multiplier
                    )
                )
                upper = int(
                    round(
                        max(totals)
                        * profile.traffic_multiplier
                        * profile.budget_multiplier
                    )
                )
                runtime_sku = primary_region.get(
                    "runtime_sku",
                    "AWS runtime"
                )
                service_breakdown = primary_region.get(
                    "service_breakdown",
                    []
                )
                raw_line_items = pricing_data.get(
                    "line_items",
                    []
                )
                line_items = (
                    raw_line_items
                    if isinstance(
                        raw_line_items,
                        list
                    )
                    else []
                ) or [
                    (
                        f"AWS runtime "
                        f"({runtime_sku}) in "
                        f"{primary_region['region']}: "
                        f"{currency} "
                        f"{float(primary_region.get('runtime_monthly', 0)):.2f}/month"
                    )
                ] + [
                    (
                        f"{service.get('component', 'Service')}: "
                        f"{service.get('recommended', 'Managed service')}: "
                        f"{service.get('currency', currency)} "
                        f"{float(service.get('monthly_cost', 0)):.2f}/month"
                    )
                    for service in service_breakdown
                ]
                line_items.extend(
                    _pricing_adjustment_lines(
                        profile
                    )
                )
                raw_assumptions = pricing_data.get(
                    "assumptions",
                    []
                )
                assumptions = (
                    raw_assumptions
                    if isinstance(
                        raw_assumptions,
                        list
                    )
                    else []
                ) or [
                    (
                        "Summary pricing uses the lowest AWS region "
                        "from the regional comparison."
                    ),
                    (
                        f"Estimated application sizing: {cloud_sizing.cpu_cores} "
                        f"vCPU, {cloud_sizing.memory_gb} GB RAM, "
                        f"{cloud_sizing.storage_gb} GB storage."
                    ),
                    f"Expected traffic profile: {profile.traffic_label} ({profile.sizing_reason}).",
                    f"Budget posture: {profile.budget_label} ({profile.service_posture}).",
                    f"Migration goal: {profile.goal_label}.",
                    f"Migration timeline: {profile.timeline_label} ({profile.timeline_posture}).",
                    (
                        "Runtime pricing retrieved from AWS Price List API. "
                        "Managed service rows use AWS Pricing API where practical "
                        "and conservative usage assumptions for low-volume services."
                    ),
                ]

                return CostEstimate(
                    currency=currency,
                    monthly=monthly,
                    monthly_range=(
                        f"{currency} {lower:,} - {upper:,}/month"
                    ),
                    annual=annual,
                    line_items=line_items,
                    assumptions=assumptions,
                    regional_prices=regional_prices,
                )

    line_items: list[str] = []

    if "Azure Functions" in analysis.frameworks:

        base = 4500

        line_items.append(
            "Azure Functions Premium/Consumption baseline: INR 3,000-6,000/month for a small event-driven workload."
        )

    else:

        base = 6000

        line_items.append(
            "Managed application runtime: INR 5,000-8,000/month for small production compute."
        )

    if (
        request.requirements.expected_traffic.value
        == "Medium"
    ):

        base += 4000

        line_items.append(
            "Medium traffic capacity buffer: INR 4,000/month."
        )

    if (
        request.requirements.expected_traffic.value
        == "High"
    ):

        base += 10000

        line_items.append(
            "High traffic capacity buffer: INR 10,000/month."
        )

    if analysis.databases:

        base += 3500

        line_items.append(
            "Managed database estimate: INR 3,500/month."
        )

    if (
        analysis.cloud_dependencies
        or analysis.storage_dependencies
    ):

        base += 1200

        line_items.append(
            "Storage and cloud dependency allowance: INR 1,200/month."
        )

    line_items.append(
        "Monitoring/log analytics allowance: INR 1,000-2,000/month depending on retained logs."
    )

    if (
        request.requirements.budget_preference.value
        == "Performance Focused"
    ):

        base = int(base * 1.45)

    if (
        request.requirements.budget_preference.value
        == "Low Cost"
    ):

        base = int(base * 0.8)

    lower = int(base * 0.85)
    upper = int(base * 1.2)

    return CostEstimate(
        currency="INR",
        monthly=base,
        monthly_range=(
            f"INR {lower:,} - INR {upper:,}/month"
        ),
        annual=base * 12,
        line_items=line_items,
        assumptions=[
            (
                f"Expected traffic profile: "
                f"{request.requirements.expected_traffic.value}"
            ),
            f"Migration goal: {profile.goal_label}",
            f"Budget posture: {profile.budget_label} ({profile.service_posture})",
            f"Migration timeline: {profile.timeline_label} ({profile.timeline_posture})",
            f"Sizing profile: {profile.cpu_cores} vCPU, {profile.memory_gb} GB RAM, {profile.storage_gb} GB storage",
            (
                f"Hosting model detected: "
                f"{analysis.hosting_model}"
            ),
            (
                "Estimate includes managed runtime, "
                "storage, secrets and monitoring."
            ),
        ],
    )
    
def _modernization_opportunities(
    analysis: RepositoryAnalysis,
    provider: str,
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> list[str]:
    """Build deterministic modernization recommendations for the detected stack.

    Args:
        analysis: Repository analysis containing stack and dependency signals.
        provider: Selected cloud provider.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Deduplicated modernization opportunity strings.
    """
    cloud = SERVICE_MAP[provider]
    stack = _join(
        analysis.frameworks
        or analysis.runtimes
        or analysis.languages
    )
    opportunities = [
        (
            f"Externalize configuration and secrets for the detected "
            f"{stack} workload into {cloud['secrets']}."
        ),
        (
            f"Centralize application logs and runtime metrics from "
            f"{stack} into {cloud['monitoring']}."
        ),
    ]

    if "Azure Functions" in analysis.frameworks:
        opportunities.append("Keep the workload serverless and evaluate Azure Functions Premium Plan only if cold start, VNet, or scaling guarantees are required.")
        opportunities.append("Enable managed identity for function-to-storage and function-to-secret access.")

    if analysis.databases:
        opportunities.append(
            (
                f"Plan managed database migration for {_join(analysis.databases)} "
                f"using {cloud['database']}."
            )
        )

    if analysis.package_managers:
        opportunities.append(
            (
                f"Add dependency restore, vulnerability scanning, and build "
                f"validation for {_join(analysis.package_managers)} packages."
            )
        )

    if "Azure Functions" in analysis.frameworks:
        opportunities.append(f"Deploy function code to {cloud['function']} rather than introducing containers unless custom runtime needs appear.")
    elif not analysis.container_configs:
        opportunities.append(
            (
                f"Add a Dockerfile for the detected {stack} application "
                f"so it can be deployed repeatably to {cloud['container']}."
            )
        )
    else:
        opportunities.append(
            (
                f"Use existing container configuration ({_join(analysis.container_configs)}) "
                f"as the deployment base for {cloud['container']}."
            )
        )

    if not analysis.cicd_configs:
        opportunities.append(
            (
                f"Add CI/CD workflow for {_join(analysis.package_managers) if analysis.package_managers else 'the detected application stack'} "
                "with build, test, scan, approval, and deployment stages."
            )
        )
    else:
        opportunities.append(
            (
                f"Extend detected CI/CD configuration ({_join(analysis.cicd_configs)}) "
                f"with cloud deployment approvals and post-deploy smoke tests."
            )
        )

    if analysis.governance_findings:
        opportunities.append("Resolve governance findings before production cutover.")

    opportunities.extend(
        _requirement_opportunities(
            request,
            profile,
            provider
        )
    )

    return _dedupe(opportunities)

def _roadmap(
    strategy: str,
    analysis: RepositoryAnalysis,
    provider: str,
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> list[str]:
    """Generate an end-to-end migration roadmap for the target provider.

    Args:
        strategy: Recommended migration strategy.
        analysis: Repository analysis containing stack and dependency signals.
        provider: Selected cloud provider.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Ordered migration roadmap steps.
    """
    cloud = SERVICE_MAP[provider]
    stack = _join(
        analysis.frameworks
        or analysis.runtimes
        or analysis.languages
    )
    runtime_target = (
        cloud["function"]
        if "Azure Functions" in analysis.frameworks
        else cloud["container"]
    )
    package_step = (
        f"validate {_join(analysis.package_managers)} dependency restore and build commands"
        if analysis.package_managers
        else "document dependency restore and build commands"
    )
    sizing = analysis.cloud_sizing
    sizing_text = (
        f"{profile.cpu_cores} vCPU and {profile.memory_gb} GB RAM"
        if sizing
        else f"{profile.cpu_cores} vCPU and {profile.memory_gb} GB RAM requirement profile"
    )

    steps = [
        (
            f"Discovery and scope: confirm the {stack} application modules, owners, "
            f"business critical paths, {strategy.lower()} success criteria, target environments, "
            "and rollback decision points."
        ),
        (
            f"Repository and build assessment: inventory detected runtimes ({_join(analysis.runtimes)}), "
            f"frameworks ({_join(analysis.frameworks)}), package managers "
            f"({_join(analysis.package_managers) if analysis.package_managers else 'not detected'}), "
            f"entry points ({_join(analysis.triggers) if analysis.triggers else 'not detected'}), "
            f"and {package_step}."
        ),
        (
            f"Dependency mapping: validate application dependencies including databases "
            f"({_join(analysis.databases) if analysis.databases else 'not detected'}), cloud services "
            f"({_join(analysis.cloud_dependencies) if analysis.cloud_dependencies else 'not detected'}), "
            f"external integrations ({_join(analysis.external_dependencies) if analysis.external_dependencies else 'not detected'}), "
            f"storage requirements ({_join(analysis.storage_dependencies) if analysis.storage_dependencies else 'not detected'}), "
            "ports, background jobs, and environment-specific configuration."
        ),
        (
            f"Target architecture design: map the current {analysis.hosting_model} hosting model "
            f"and {analysis.deployment_model} deployment model to {provider} services such as "
            f"{runtime_target}, {cloud['database']}, {cloud['storage']}, {cloud['secrets']}, "
            f"and {cloud['monitoring']}."
        ),
        (
            f"Landing zone setup: provision {provider} accounts/projects, resource groups, "
            "network segmentation, private access where required, IAM/RBAC roles, tagging, "
            "audit logging, and separate dev, test, and production environments."
        ),
    ]

    if "Azure Functions" in analysis.frameworks:
        steps.append(
            (
                f"Runtime preparation: configure the target serverless runtime on {runtime_target}, "
                "including triggers, bindings, app settings, managed identity, scaling limits, "
                f"and {sizing_text} capacity assumptions."
            )
        )
    elif analysis.container_configs:
        steps.append(
            (
                f"Runtime preparation: validate existing container artifacts "
                f"({_join(analysis.container_configs)}), harden the image, publish it to "
                f"{cloud['registry']}, and deploy it to {runtime_target} with {sizing_text}."
            )
        )
    else:
        steps.append(
            (
                f"Runtime preparation: create a Dockerfile or deployment package for the {stack} "
                f"workload, validate local build/run behavior, publish artifacts to {cloud['registry']}, "
                f"and size the target {runtime_target} environment using {sizing_text}."
            )
        )

    if analysis.databases:
        steps.append(
            (
                f"Database and data migration: migrate {_join(analysis.databases)} schema and data "
                f"to {cloud['database']} using backup/restore or migration tooling, then validate "
                "row counts, stored procedures, indexes, connection strings, and rollback backups."
            )
        )

    if analysis.cloud_dependencies:
        steps.append(
            (
                f"Cloud service integration: replace or reconfigure detected cloud dependencies "
                f"({_join(analysis.cloud_dependencies)}) with target {provider} services, managed identity, "
                "least-privilege access, retry policies, and environment-specific endpoints."
            )
        )

    steps.append(
        (
            f"Configuration and secrets: move application settings, connection strings, API keys, "
            f"and runtime environment values into {cloud['secrets']} and configure secure injection "
            "for dev, test, and production deployments."
        )
    )

    if analysis.cicd_configs:
        steps.append(
            (
                f"CI/CD and infrastructure automation: extend detected pipeline configuration "
                f"({_join(analysis.cicd_configs)}) with dependency restore, tests, security scans, "
                "infrastructure deployment, approval gates, smoke tests, and rollback tasks."
            )
        )
    else:
        steps.append(
            (
                f"CI/CD and infrastructure automation: add a pipeline for "
                f"{_join(analysis.package_managers) if analysis.package_managers else stack} build, "
                "unit tests, security scans, infrastructure provisioning, approvals, deployment, "
                "and rollback automation."
            )
        )

    steps.extend(
        [
            (
                f"Observability setup: configure {cloud['monitoring']} dashboards, application logs, "
                "metrics, alerts, distributed tracing where supported, release annotations, and "
                "retention policies for the migrated workload."
            ),
            (
                f"Validation and performance testing: run smoke, integration, regression, and load "
                f"tests for detected HTTP/runtime flows "
                f"({_join(analysis.triggers) if analysis.triggers else 'application entry points'}), "
                "validate database behavior, verify security controls, and complete rollback rehearsal."
            ),
            (
                f"Production cutover: execute the {strategy.lower()} migration using a controlled "
                "deployment window, DNS or traffic switch, database freeze or synchronization plan, "
                "real-time monitoring, and a clear rollback threshold."
            ),
            (
                f"Post-migration optimization: review {stack} live traffic, right-size compute, "
                "tune database and storage costs, close temporary migration access, update runbooks, "
                "and hand over operational ownership."
            ),
        ]
    )

    steps.extend(
        _requirement_roadmap_steps(
            request,
            profile,
            provider
        )
    )

    return _dedupe(steps)

def _architecture_summary(analysis: RepositoryAnalysis) -> str:
    """Return the most specific available architecture summary.

    Args:
        analysis: Repository analysis for the application.

    Returns:
        One-sentence architecture summary.
    """
    if analysis.project_summary and analysis.project_summary != "Unknown":
        return analysis.project_summary
    if "Azure Functions" in analysis.frameworks:
        triggers = f" Triggers: {_join(analysis.triggers)}." if analysis.triggers else ""
        return f"{analysis.architecture_pattern}. Hosting model: {analysis.hosting_model}. Runtime: {_join(analysis.runtimes)}.{triggers}"
    readiness = "Container Ready" if analysis.container_configs else "Requires Containerization"
    return f"{analysis.architecture_pattern}. {readiness}. Detected stack includes {_join(analysis.frameworks or analysis.languages)}."

def _governance(
    analysis: RepositoryAnalysis,
    provider: str,
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> GovernanceAssessment:
    """Create deterministic security and governance assessment guidance.

    Args:
        analysis: Repository analysis containing governance and stack signals.
        provider: Selected cloud provider.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Governance assessment with issues, checks, recommendations, and risk.
    """
    issues = list(analysis.governance_findings)
    passed_checks: list[str] = []
    cloud = SERVICE_MAP[provider]
    stack = _join(
        analysis.frameworks
        or analysis.runtimes
        or analysis.languages
    )
    recommendations = [
        (
            f"Store {stack} secrets, connection strings, and environment values "
            f"in {cloud['secrets']}."
        ),
        (
            f"Enable centralized logs, metrics, alerts, and retention policies "
            f"with {cloud['monitoring']}."
        ),
        (
            f"Add {provider} RBAC review and least-privilege deployment "
            "permissions before production cutover."
        ),
    ]

    if not analysis.governance_findings:
        passed_checks.append("No hardcoded credentials, public storage ACLs, debug flags, or open container ports were detected in scanned files.")
    if analysis.package_managers:
        passed_checks.append(
            (
                f"Package dependency metadata was detected "
                f"({_join(analysis.package_managers)}) for repeatable builds."
            )
        )
        recommendations.append(
            (
                f"Add dependency scanning and lockfile review for "
                f"{_join(analysis.package_managers)} packages."
            )
        )
    else:
        issues.append(
            (
                f"No package manager metadata was detected for the {stack} workload, "
                "so dependency restore and vulnerability scanning need manual definition."
            )
        )
    if "Azure Functions" in analysis.frameworks:
        passed_checks.append("Serverless runtime reduces host and container patching responsibility.")
    if analysis.container_configs:
        passed_checks.append(
            (
                f"Container configuration was detected "
                f"({_join(analysis.container_configs)}), supporting portable deployment."
            )
        )
    if analysis.cicd_configs:
        passed_checks.append(
            (
                f"CI/CD configuration was detected ({_join(analysis.cicd_configs)})."
            )
        )
    if analysis.infrastructure_configs:
        passed_checks.append(
            (
                f"Infrastructure-as-code configuration was detected "
                f"({_join(analysis.infrastructure_configs)})."
            )
        )

    if not analysis.cicd_configs:
        issues.append(
            (
                f"No CI/CD workflow was detected for the {stack} workload."
            )
        )
    if not analysis.infrastructure_configs:
        issues.append(
            (
                f"No infrastructure-as-code configuration was detected for "
                f"provisioning {provider} resources."
            )
        )
    if request.requirements.migration_timeline.value == "Immediate":
        issues.append(
            "Immediate timeline increases migration risk because discovery, validation, and rollback rehearsal are compressed."
        )
    if request.requirements.expected_traffic.value == "High":
        recommendations.append(
            f"Define high-traffic alert thresholds, autoscaling guardrails, and capacity runbooks in {cloud['monitoring']} before cutover."
        )
    if request.requirements.budget_preference.value == "Low Cost":
        recommendations.append(
            f"Add budget alerts, mandatory tags, and rightsizing reviews for {provider} resources."
        )
    if request.requirements.migration_timeline.value in {"6 Months", "Flexible"}:
        passed_checks.append(
            "Selected timeline allows deeper validation, staged rollout, and rollback rehearsal before production cutover."
        )
    if not analysis.container_configs and "Azure Functions" not in analysis.frameworks:
        issues.append(
            (
                f"No container configuration was detected for the {stack} application."
            )
        )
    if analysis.databases:
        recommendations.append(
            (
                f"Validate {_join(analysis.databases)} backup, restore, encryption, "
                "and migration permissions before cutover."
            )
        )
        if not analysis.infrastructure_configs:
            issues.append(
                (
                    f"Detected {_join(analysis.databases)} dependency has no matching "
                    "infrastructure-as-code definition for repeatable database provisioning."
                )
            )
    else:
        passed_checks.append(
            "No persistent database dependency was detected in scanned files."
        )

    high_risk_tokens = ["secret", "credential", "public storage", "open container"]
    if any(any(token in issue.lower() for token in high_risk_tokens) for issue in issues):
        risk = "High"
    elif len(issues) >= 2:
        risk = "Medium"
    else:
        risk = "Low"

    risk = _adjust_risk(
        risk,
        profile.risk_modifier
    )

    recommendation = (
        "Block production migration until high-risk findings are remediated."
        if risk == "High"
        else "Address governance gaps during migration planning."
        if risk == "Medium"
        else "Proceed with standard security validation and approval gates."
    )
    return GovernanceAssessment(
        risk_level=risk,
        issues=sorted(set(issues)),
        passed_checks=sorted(set(passed_checks)),
        recommendations=recommendations,
        recommendation=recommendation,
    )

def _requirement_opportunities(
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile,
    provider: str
) -> list[str]:
    """Return modernization opportunities driven by selected migration inputs.

    Args:
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.
        provider: Selected cloud provider.

    Returns:
        Requirement-specific modernization opportunity strings.
    """
    items: list[str] = [
        (
            f"Apply a {profile.service_posture} target architecture for "
            f"{profile.goal_label.lower()} using {profile.cpu_cores} vCPU, "
            f"{profile.memory_gb} GB RAM, and {profile.storage_gb} GB storage as the planning baseline."
        )
    ]

    if request.requirements.migration_goal.value == "Cost Optimization":
        items.append(
            f"Introduce {provider} budget alerts, resource tags, rightsizing reviews, and scheduled cleanup for non-production resources."
        )
    if request.requirements.migration_goal.value == "Scalability":
        items.append(
            "Define autoscaling thresholds, load test targets, and peak traffic runbooks before production migration."
        )
    if request.requirements.migration_goal.value == "Performance Improvement":
        items.append(
            "Add performance baselines, latency budgets, profiling, and database/query tuning checkpoints."
        )
    if request.requirements.expected_traffic.value == "High":
        items.append(
            "Plan CDN/WAF, autoscaling, and higher observability retention for high expected traffic."
        )
    if request.requirements.budget_preference.value == "Low Cost":
        items.append(
            "Prefer serverless or smaller managed tiers first, then scale after measured utilization justifies it."
        )
    if request.requirements.budget_preference.value == "Performance Focused":
        items.append(
            "Prefer performance-oriented runtime and database tiers with stricter monitoring and alerting."
        )

    return items

def _requirement_roadmap_steps(
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile,
    provider: str
) -> list[str]:
    """Return roadmap steps driven by traffic, budget, goal, and timeline.

    Args:
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.
        provider: Selected cloud provider.

    Returns:
        Requirement-specific roadmap steps.
    """
    steps = [
        (
            f"Requirement profile validation: confirm {profile.traffic_label} traffic assumptions, "
            f"{profile.budget_label} budget posture, {profile.goal_label.lower()} objective, "
            f"and {profile.timeline_label} delivery window with application owners."
        ),
        (
            f"Planning impact: use {profile.cpu_cores} vCPU, {profile.memory_gb} GB RAM, "
            f"{profile.storage_gb} GB storage, {profile.service_posture} service posture, "
            f"and {profile.timeline_posture}."
        )
    ]

    if request.requirements.expected_traffic.value == "Low":
        steps.append(
            "Capacity validation: start with minimal production capacity and define scale-up triggers based on CPU, memory, request volume, and error rate."
        )
    elif request.requirements.expected_traffic.value == "Medium":
        steps.append(
            "Capacity validation: run moderate load testing, configure autoscaling minimums, and validate log/metric retention for normal production traffic."
        )
    else:
        steps.append(
            "Capacity validation: run peak-load and soak tests, configure autoscaling limits, CDN/WAF rules, and high-traffic rollback thresholds."
        )

    if request.requirements.migration_timeline.value == "Immediate":
        steps.append(
            "Timeline control: reduce scope to the safest migration path, freeze optional refactoring, and require a documented rollback checkpoint."
        )
    elif request.requirements.migration_timeline.value in {"6 Months", "Flexible"}:
        steps.append(
            "Timeline control: include staged pilots, security review, performance tuning, cost review, and operational handover before cutover."
        )

    if request.requirements.budget_preference.value == "Low Cost":
        steps.append(
            f"Cost control: enable {provider} budgets, tagging, low-cost region comparison, and post-migration rightsizing review."
        )
    elif request.requirements.budget_preference.value == "Performance Focused":
        steps.append(
            "Performance control: validate higher-capacity runtime, database performance, and observability dashboards before production traffic shift."
        )

    return steps

def _apply_requirement_opportunities(
    opportunities: list[str],
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> list[str]:
    """Merge generated opportunities with requirement-specific recommendations.

    Args:
        opportunities: Existing modernization opportunities.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Deduplicated modernization opportunities.
    """
    provider = request.requirements.cloud_provider.value
    if provider == "No Preference":
        provider = "the selected cloud provider"
    return _dedupe(
        [
            *opportunities,
            *_requirement_opportunities(
                request,
                profile,
                provider
            )
        ]
    )

def _apply_requirement_roadmap(
    roadmap: list[str],
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> list[str]:
    """Merge generated roadmap steps with requirement-specific execution tasks.

    Args:
        roadmap: Existing roadmap steps.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Deduplicated roadmap steps.
    """
    provider = request.requirements.cloud_provider.value
    if provider == "No Preference":
        provider = "the selected cloud provider"
    return _dedupe(
        [
            *roadmap,
            *_requirement_roadmap_steps(
                request,
                profile,
                provider
            )
        ]
    )

def _apply_requirement_governance(
    governance: GovernanceAssessment,
    request: AssessmentRequest | FolderAssessmentRequest,
    profile: RequirementsProfile
) -> GovernanceAssessment:
    """Adjust governance output using selected risk and planning requirements.

    Args:
        governance: Existing governance assessment.
        request: Assessment request containing migration requirements.
        profile: Normalized requirements profile.

    Returns:
        Governance assessment after requirement-specific adjustments.
    """
    recommendations = list(governance.recommendations)
    issues = list(governance.issues)
    passed_checks = list(governance.passed_checks)

    if request.requirements.migration_timeline.value == "Immediate":
        issues.append(
            "Immediate timeline requires explicit rollback approval and reduced migration scope."
        )
    if request.requirements.expected_traffic.value == "High":
        recommendations.append(
            "High expected traffic requires autoscaling, alerting, and load-test evidence before approval."
        )
    if request.requirements.budget_preference.value == "Low Cost":
        recommendations.append(
            "Low-cost posture requires budget alerts, resource tags, and scheduled rightsizing reviews."
        )
    if request.requirements.migration_timeline.value in {"6 Months", "Flexible"}:
        passed_checks.append(
            "Selected timeline supports staged validation and governance checkpoints."
        )

    risk = _adjust_risk(
        governance.risk_level,
        profile.risk_modifier
    )
    recommendation = (
        "Block production migration until high-risk findings are remediated."
        if risk == "High"
        else "Address governance gaps during migration planning."
        if risk == "Medium"
        else "Proceed with standard security validation and approval gates."
    )

    return GovernanceAssessment(
        risk_level=risk,
        issues=sorted(set(issues)),
        passed_checks=sorted(set(passed_checks)),
        recommendations=_dedupe(recommendations),
        recommendation=recommendation,
    )

def _adjust_risk(
    risk: str,
    modifier: int
) -> str:
    """Move a risk label up or down by the requested modifier.

    Args:
        risk: Current risk label.
        modifier: Positive or negative number of risk levels to move.

    Returns:
        Adjusted risk label.
    """
    levels = ["Low", "Medium", "High"]
    index = levels.index(risk) if risk in levels else 1
    return levels[
        max(
            0,
            min(
                len(levels) - 1,
                index + modifier
            )
        )
    ]

def _user_visible_warnings(warnings: list[str]) -> list[str]:
    """Hide internal LLM fallback warnings before returning the API response.

    Args:
        warnings: Raw warnings collected during assessment generation.

    Returns:
        Warnings safe to display in the UI.
    """
    internal_prefixes = (
        "Groq is not configured.",
        "LLM repository analysis",
        "LLM migration guidance",
        "LLM service recommendation",
        "AWS pricing LLM",
    )
    return [
        warning
        for warning in warnings
        if not warning.startswith(internal_prefixes)
    ]

def _join(items: list[str]) -> str:
    """Join list values for report text, or return Not detected for empty input.

    Args:
        items: Values to join.

    Returns:
        Comma-separated values or "Not detected".
    """
    return ", ".join(items) if items else "Not detected"

def _dedupe(items: list[str]) -> list[str]:
    """Return unique strings while preserving original order.

    Args:
        items: Values to deduplicate.

    Returns:
        Deduplicated values in first-seen order.
    """
    deduped: list[str] = []
    seen: set[str] = set()

    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)

    return deduped

def _dedupe_services(
    services: list[ServiceRecommendation]
) -> list[ServiceRecommendation]:
    """Return one recommendation per service component.

    Args:
        services: Service recommendations that may contain duplicate components.

    Returns:
        Deduplicated service recommendations.
    """
    deduped: list[ServiceRecommendation] = []
    seen: set[str] = set()

    for service in services:
        key = service.component.strip().lower()
        if key in seen:
            continue
        deduped.append(service)
        seen.add(key)

    return deduped

def _bullet_list(items: list[str]) -> str:
    """Render Markdown bullets, using None when there are no rows.

    Args:
        items: Values to render as Markdown bullets.

    Returns:
        Markdown bullet list text.
    """
    return "\n".join(f"- {item}" for item in items) if items else "- None"
