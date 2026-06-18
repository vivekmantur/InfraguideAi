from __future__ import annotations
from uuid import uuid4
from .ai import (
    generate_architect_reasoning,
    generate_aws_pricing_estimate,
    generate_migration_guidance,
    generate_service_recommendations,
)
from .migration_strategy import determine_migration_strategy, assess_strategy_alignment
from app.services.mcp_client import (
    CloudMcpClient
)
from .models import (
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
from .storage import utc_now


SERVICE_MAP = {
    "Azure": {
        "container": "Azure Container Apps",
        "function": "Azure Functions Premium Plan",
        "database": "Azure SQL Database / Azure Database for PostgreSQL",
        "storage": "Azure Blob Storage",
        "secrets": "Azure Key Vault",
        "monitoring": "Azure Monitor",
    },
    "AWS": {
        "container": "Amazon ECS Fargate",
        "function": "AWS Lambda",
        "database": "Amazon RDS",
        "storage": "Amazon S3",
        "secrets": "AWS Secrets Manager",
        "monitoring": "Amazon CloudWatch",
    },
    "GCP": {
        "container": "Cloud Run",
        "function": "Cloud Functions",
        "database": "Cloud SQL",
        "storage": "Cloud Storage",
        "secrets": "Secret Manager",
        "monitoring": "Cloud Monitoring",
    },
}


async def build_assessment(request: AssessmentRequest | FolderAssessmentRequest, analysis: RepositoryAnalysis, warnings: list[str]) -> AssessmentResponse:
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
    print(f"analysis: {analysis},provider:{provider}")
    fallback_services = _services(provider, analysis)
    services, service_warnings = generate_service_recommendations(
        analysis,
        request.requirements,
        provider,
        strategy_result,
        fallback_services,
    )
    warnings.extend(service_warnings)
    print(f"Recommended services for provider {services}")
    print(request.requirements.cloud_provider)
    cost = await _cost_estimate(request, analysis, services)
    print(f"Cost estimate for provider {provider}: {cost.monthly} INR/month with line items: {cost.line_items}")
    fallback_opportunities = _modernization_opportunities(analysis, provider)
    strategy = strategy_result.strategy
    fallback_roadmap = _roadmap(strategy, analysis, provider)
    architecture_summary = _architecture_summary(analysis)
    fallback_governance = _governance(analysis, provider)
    governance, opportunities, roadmap, guidance_warnings = generate_migration_guidance(
        analysis,
        request.requirements,
        provider,
        strategy_result,
        [item.model_dump() for item in services],
        fallback_governance,
        fallback_opportunities,
        fallback_roadmap,
    )
    warnings.extend(guidance_warnings)
    ai_reasoning = generate_architect_reasoning(
        analysis,
        provider,
        [item.model_dump() for item in services],
        cost.model_dump(),
        roadmap,
        strategy_result
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
    if request.requirements.cloud_provider.value != "No Preference":
        return request.requirements.cloud_provider.value
    if "Azure Functions" in analysis.frameworks or "ASP.NET Core" in analysis.frameworks or "SQL Server" in analysis.databases:
        return "Azure"
    if request.requirements.budget_preference.value == "Low Cost":
        return "GCP"
    return "AWS"


def _readiness(analysis: RepositoryAnalysis) -> ReadinessAssessment:
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


def _services(provider: str, analysis: RepositoryAnalysis) -> list[ServiceRecommendation]:
    cloud = SERVICE_MAP[provider]
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
    return services


async def _cost_estimate(
    request: AssessmentRequest | FolderAssessmentRequest,
    analysis: RepositoryAnalysis,
    services: list[ServiceRecommendation] | None = None
) -> CostEstimate:

    provider = _select_provider(
        request,
        analysis
    )

    # --------------------------------------------------
    # GCP Pricing Through MCP
    # --------------------------------------------------



    if provider in {"GCP", "Azure"}:

        cloud_sizing = (
            analysis.cloud_sizing
            if analysis.cloud_sizing
            else CloudSizingRequirements()
        )

        if not analysis.cloud_sizing:

            print(
                "Cloud sizing was not detected. "
                "Using default sizing for live pricing: "
                f"{cloud_sizing.cpu_cores} vCPU, "
                f"{cloud_sizing.memory_gb} GB RAM."
            )

        cpu = cloud_sizing.cpu_cores
        memory = cloud_sizing.memory_gb

        mcp_client = CloudMcpClient()

        # -----------------------------------------
        # GCP
        # -----------------------------------------

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
                print(
                    "GCP compute pricing request failed before "
                    "a usable response was returned:"
                )
                print(ex)

            print(
                "GCP Pricing Response:",
                pricing
            )

            if pricing is None:

                print(
                    "MCP returned None. "
                    "Falling back to heuristic pricing."
                )

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

                        print(
                            "GCP service pricing failed:"
                        )
                        print(ex)

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

                    elif service_pricing:

                        print(
                            "GCP service pricing returned error:"
                        )
                        print(service_pricing)

                total_monthly = monthly + additional_monthly

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
                        )
                    ] + additional_line_items,
                    assumptions=[
                        (
                            f"Machine type selected: "
                            f"{pricing['machine_type']}"
                        ),
                        f"CPU requirement: {cpu}",
                        f"Memory requirement: {memory}",
                        (
                            "Cost calculated using "
                            "Google Cloud Billing API"
                        )
                    ] + additional_assumptions,
                    regional_prices=regional_prices,
                )

            else:

                print(
                    "GCP pricing failed:"
                )

                print(pricing)

                print(
                    "Falling back to "
                    "heuristic pricing."
                )

        # -----------------------------------------
        # Azure
        # -----------------------------------------

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
                print(
                    "Azure VM pricing request failed before "
                    "a usable response was returned:"
                )
                print(ex)

            print(
                "Azure Pricing Response:",
                pricing
            )

            if pricing is None:

                print(
                    "MCP returned None. "
                    "Falling back to heuristic pricing."
                )

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

                        print(
                            "Azure service pricing failed:"
                        )
                        print(ex)

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

                    elif service_pricing:

                        print(
                            "Azure service pricing returned error:"
                        )
                        print(service_pricing)

                total_monthly = monthly + additional_monthly

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
                        )
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
                        (
                            "Cost calculated using "
                            "Azure Retail Pricing API"
                        )
                    ] + additional_assumptions,
                    regional_prices=regional_prices,
                )

            else:

                print(
                    "Azure pricing failed:"
                )

                print(pricing)

                print(
                    "Falling back to "
                    "heuristic pricing."
                )
    # --------------------------------------------------
    # AWS Pricing Through Groq
    # --------------------------------------------------

    if provider == "AWS":

        cloud_sizing = (
            analysis.cloud_sizing
            if analysis.cloud_sizing
            else CloudSizingRequirements()
        )

        pricing_data, pricing_warnings = (
            generate_aws_pricing_estimate(
                analysis,
                request.requirements,
                [
                    service.model_dump()
                    for service in (services or [])
                ],
                cloud_sizing,
            )
        )

        for warning in pricing_warnings:
            print(warning)

        if pricing_data:

            regional_prices = [
                row
                for row in pricing_data.get(
                    "regional_prices",
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
                    )
                )
                annual = int(
                    monthly * 12
                )
                lower = int(
                    round(
                        min(totals)
                    )
                )
                upper = int(
                    round(
                        max(totals)
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
                        "Summary pricing uses the lowest estimated "
                        "AWS region from the regional comparison."
                    ),
                    (
                        f"Estimated application sizing: {cloud_sizing.cpu_cores} "
                        f"vCPU, {cloud_sizing.memory_gb} GB RAM, "
                        f"{cloud_sizing.storage_gb} GB storage."
                    ),
                    (
                        "Regional pricing was estimated by Groq using "
                        "current AWS service pricing patterns."
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

        print(
            "AWS pricing LLM estimate failed. "
            "Falling back to heuristic pricing."
        )

    # --------------------------------------------------
    # Existing heuristic pricing
    # --------------------------------------------------

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
    

def _modernization_opportunities(analysis: RepositoryAnalysis, provider: str) -> list[str]:
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

    return _dedupe(opportunities)


def _strategy(request: AssessmentRequest | FolderAssessmentRequest, readiness: ReadinessAssessment) -> str:
    goal = request.requirements.migration_goal.value
    if goal == "Lift-and-Shift":
        return "Rehost"
    if goal in {"Application Modernization", "Scalability", "Performance Improvement"}:
        return "Replatform" if readiness.score >= 65 else "Refactor"
    return "Replatform"


def _roadmap(strategy: str, analysis: RepositoryAnalysis, provider: str) -> list[str]:
    stack = _join(
        analysis.frameworks
        or analysis.runtimes
        or analysis.languages
    )
    package_step = (
        f"validate {_join(analysis.package_managers)} dependency restore and build commands"
        if analysis.package_managers
        else "document dependency restore and build commands"
    )

    if "Azure Functions" in analysis.frameworks:
        steps = [
            (
                f"Repository Preparation: document detected serverless runtime "
                f"({_join(analysis.runtimes)}) triggers, app settings, bindings, "
                f"and {package_step}."
            ),
            (
                f"Serverless Runtime Setup: create target {provider} function runtime, "
                "storage account, managed identity, secrets, and monitoring workspace."
            ),
        ]
    else:
        steps = [
            (
                f"Repository Preparation: document detected {stack} runtime, "
                f"environment variables, and {package_step}."
            ),
        ]

        if analysis.container_configs:
            steps.append(
                (
                    f"Containerization: validate existing container artifacts "
                    f"({_join(analysis.container_configs)}) and publish a versioned image."
                )
            )
        else:
            steps.append(
                (
                    f"Containerization: create a Dockerfile for the {stack} workload "
                    "and verify local build/run behavior."
                )
            )

    if analysis.cicd_configs:
        steps.append(
            (
                f"CI/CD: extend detected pipeline configuration ({_join(analysis.cicd_configs)}) "
                "with image build, security scan, approval, and deployment stages."
            )
        )
    else:
        steps.append(
            (
                f"CI/CD: add a pipeline for {_join(analysis.package_managers) if analysis.package_managers else stack} "
                "build, test, security scan, approval, and cloud deployment."
            )
        )

    if analysis.databases:
        steps.append(
            (
                f"Database Migration: plan {_join(analysis.databases)} schema migration, "
                "backup, validation, connection string rotation, and managed database cutover."
            )
        )

    steps.extend(
        [
            (
                f"Cloud Service Setup: provision target {provider} runtime for {stack}, "
                "storage, secrets, monitoring, and network access."
            ),
            (
                f"Validation: run smoke tests for detected HTTP/runtime flows "
                f"({_join(analysis.triggers) if analysis.triggers else 'application entry points'}), "
                "performance checks, security review, and rollback rehearsal."
            ),
            (
                f"Production Cutover: execute {strategy.lower()} migration, monitor "
                f"{stack} live traffic, and optimize cloud costs."
            ),
        ]
    )

    return _dedupe(steps)


def _architecture_summary(analysis: RepositoryAnalysis) -> str:
    if analysis.project_summary and analysis.project_summary != "Unknown":
        return analysis.project_summary
    if "Azure Functions" in analysis.frameworks:
        triggers = f" Triggers: {_join(analysis.triggers)}." if analysis.triggers else ""
        return f"{analysis.architecture_pattern}. Hosting model: {analysis.hosting_model}. Runtime: {_join(analysis.runtimes)}.{triggers}"
    readiness = "Container Ready" if analysis.container_configs else "Requires Containerization"
    return f"{analysis.architecture_pattern}. {readiness}. Detected stack includes {_join(analysis.frameworks or analysis.languages)}."


def _governance(analysis: RepositoryAnalysis, provider: str) -> GovernanceAssessment:
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


def _user_visible_warnings(warnings: list[str]) -> list[str]:
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
    return ", ".join(items) if items else "Not detected"


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for item in items:
        if item in seen:
            continue
        deduped.append(item)
        seen.add(item)

    return deduped


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None"
