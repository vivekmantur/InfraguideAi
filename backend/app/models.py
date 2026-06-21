from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class CloudProvider(str, Enum):
    """Supported target cloud providers."""

    aws = "AWS"
    azure = "Azure"
    gcp = "GCP"
    no_preference = "No Preference"

class MigrationGoal(str, Enum):
    """Supported migration objectives selected by the user."""

    cost = "Cost Optimization"
    modernization = "Application Modernization"
    lift_shift = "Lift-and-Shift"
    scalability = "Scalability"
    performance = "Performance Improvement"

class ExpectedTraffic(str, Enum):
    """Expected application traffic levels."""

    low = "Low"
    medium = "Medium"
    high = "High"

class BudgetPreference(str, Enum):
    """Cost and performance posture for the migration plan."""

    low_cost = "Low Cost"
    balanced = "Balanced"
    performance = "Performance Focused"

class MigrationTimeline(str, Enum):
    """Target migration delivery timelines."""

    immediate = "Immediate"
    three_months = "3 Months"
    six_months = "6 Months"
    flexible = "Flexible"

class ApprovalStatus(str, Enum):
    """Workflow approval status for a saved assessment."""

    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"

class MigrationRequirements(BaseModel):
    """User-selected migration requirements for an assessment."""

    cloud_provider: CloudProvider
    migration_goal: MigrationGoal
    expected_traffic: ExpectedTraffic
    budget_preference: BudgetPreference
    migration_timeline: MigrationTimeline

class AssessmentRequest(BaseModel):
    """Request body for GitHub repository assessments."""

    repository_url: HttpUrl
    requirements: MigrationRequirements
    github_token: Optional[str] = None

class FolderAssessmentRequest(BaseModel):
    """Request body metadata for uploaded project assessments."""

    project_name: str = "Uploaded folder"
    requirements: MigrationRequirements

class CloudSizingRequirements(BaseModel):
    """Estimated application sizing used for pricing and planning."""

    application_type: str = "Unknown"
    architecture_pattern: str = "Unknown"
    cpu_cores: int = 2
    memory_gb: int = 4
    storage_gb: int = 50
    database_type: str = "Unknown"
    database_size_gb: int = 20
    requires_load_balancer: bool = False
    requires_containerization: bool = False
    confidence: str = "Low"

class RepositoryAnalysis(BaseModel):
    """Detected repository technology, architecture, and dependency signals."""

    project_summary: str = "Unknown"
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    runtimes: List[str] = Field(default_factory=list)
    hosting_model: str = "Unknown"
    deployment_model: str = "Unknown"
    triggers: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    package_managers: List[str] = Field(default_factory=list)
    container_configs: List[str] = Field(default_factory=list)
    infrastructure_configs: List[str] = Field(default_factory=list)
    cicd_configs: List[str] = Field(default_factory=list)
    external_dependencies: List[str] = Field(default_factory=list)
    cloud_dependencies: List[str] = Field(default_factory=list)
    dependency_graph: List[str] = Field(default_factory=list)
    architecture_pattern: str = "Unknown"
    application_type: str = "Unknown"
    stateful_services: List[str] = Field(default_factory=list)
    storage_dependencies: List[str] = Field(default_factory=list)
    network_requirements: List[str] = Field(default_factory=list)
    governance_findings: List[str] = Field(default_factory=list)
    detected_files: List[str] = Field(default_factory=list)
    cloud_sizing: Optional[CloudSizingRequirements] = None
class ReadinessAssessment(BaseModel):
    """Cloud readiness scoring and compatibility findings."""

    runtime_compatibility: str
    database_compatibility: str
    container_readiness: str
    configuration_readiness: str
    score: int
    complexity: str
    findings: List[str]
    score_breakdown: List[str] = Field(default_factory=list)

class ServiceRecommendation(BaseModel):
    """Mapping from a current application component to a target cloud service."""

    component: str
    current: str
    recommended: str

class CostEstimate(BaseModel):
    """Monthly and annual cloud cost estimate with supporting line items."""

    currency: str
    monthly: int
    monthly_range: str
    annual: int
    line_items: List[str] = Field(default_factory=list)
    assumptions: List[str]
    regional_prices: List[dict] = Field(default_factory=list)

class GovernanceAssessment(BaseModel):
    """Security and governance risk assessment for the migration."""

    risk_level: str
    issues: List[str] = Field(default_factory=list)
    passed_checks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    recommendation: str

class StrategyAssessment(BaseModel):
    """Comparison between user goal and recommended migration strategy."""

    user_goal: str
    recommended_strategy: str
    confidence: str
    is_aligned: bool
    recommendation_reason: list[str]

class AssessmentResponse(BaseModel):
    """Complete migration assessment returned to the frontend."""

    id: Optional[str] = None
    created_at: Optional[str] = None
    technology_stack: RepositoryAnalysis
    architecture_summary: str
    cloud_readiness: ReadinessAssessment
    recommended_provider: str
    recommended_services: List[ServiceRecommendation]
    cost_estimation: CostEstimate
    modernization_opportunities: List[str]
    migration_strategy: str
    migration_roadmap: List[str]
    governance_assessment: GovernanceAssessment
    ai_reasoning: str
    approval_status: ApprovalStatus = ApprovalStatus.pending
    blueprint_markdown: str
    warnings: List[str] = Field(default_factory=list)
    cloud_sizing: Optional[CloudSizingRequirements] = None
    strategy_assessment: Optional[StrategyAssessment] = None

class BlueprintRequest(BaseModel):
    """Request body for rendering a blueprint document."""

    assessment: AssessmentResponse
    title: Optional[str] = "InfraGuide AI Migration Blueprint"

class ApprovalRequest(BaseModel):
    """Request body for updating assessment approval status."""

    status: ApprovalStatus
    actor: str = "demo-user"
    reason: Optional[str] = None

class AssessmentSummary(BaseModel):
    """Compact assessment record used in saved assessment lists."""

    id: str
    created_at: str
    recommended_provider: str
    readiness_score: int
    complexity: str
    approval_status: ApprovalStatus

class ChatMessage(BaseModel):
    """Single chat message exchanged with the migration assistant."""

    role: str
    content: str

class ChatRequest(BaseModel):
    """Request body for asking a question about a saved assessment."""

    assessment_id: str
    message: str
    history: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    """Response returned by the migration assistant chat endpoint."""

    answer: str
    provider: str
    model: str

class MigrationStrategyResult(BaseModel):
    """Recommended migration strategy with confidence and supporting reasons."""

    strategy: str
    confidence: str
    reasons: list[str]

