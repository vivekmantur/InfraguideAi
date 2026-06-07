from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class CloudProvider(str, Enum):
    aws = "AWS"
    azure = "Azure"
    gcp = "GCP"
    no_preference = "No Preference"


class MigrationGoal(str, Enum):
    cost = "Cost Optimization"
    modernization = "Application Modernization"
    lift_shift = "Lift-and-Shift"
    scalability = "Scalability"
    performance = "Performance Improvement"


class ExpectedTraffic(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class BudgetPreference(str, Enum):
    low_cost = "Low Cost"
    balanced = "Balanced"
    performance = "Performance Focused"


class MigrationTimeline(str, Enum):
    immediate = "Immediate"
    three_months = "3 Months"
    six_months = "6 Months"
    flexible = "Flexible"


class ApprovalStatus(str, Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"


class MigrationRequirements(BaseModel):
    cloud_provider: CloudProvider
    migration_goal: MigrationGoal
    expected_traffic: ExpectedTraffic
    budget_preference: BudgetPreference
    migration_timeline: MigrationTimeline


class AssessmentRequest(BaseModel):
    repository_url: HttpUrl
    requirements: MigrationRequirements
    github_token: Optional[str] = None


class FolderAssessmentRequest(BaseModel):
    project_name: str = "Uploaded folder"
    requirements: MigrationRequirements

class CloudSizingRequirements(BaseModel):
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
    runtime_compatibility: str
    database_compatibility: str
    container_readiness: str
    configuration_readiness: str
    score: int
    complexity: str
    findings: List[str]
    score_breakdown: List[str] = Field(default_factory=list)


class ServiceRecommendation(BaseModel):
    component: str
    current: str
    recommended: str


class CostEstimate(BaseModel):
    currency: str
    monthly: int
    monthly_range: str
    annual: int
    line_items: List[str] = Field(default_factory=list)
    assumptions: List[str]


class GovernanceAssessment(BaseModel):
    risk_level: str
    issues: List[str] = Field(default_factory=list)
    passed_checks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    recommendation: str

class StrategyAssessment(BaseModel):
    user_goal: str
    recommended_strategy: str
    confidence: str
    is_aligned: bool
    recommendation_reason: list[str]

class AssessmentResponse(BaseModel):
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
    assessment: AssessmentResponse
    title: Optional[str] = "InfraGuide AI Migration Blueprint"


class ApprovalRequest(BaseModel):
    status: ApprovalStatus
    actor: str = "demo-user"
    reason: Optional[str] = None


class AssessmentSummary(BaseModel):
    id: str
    created_at: str
    recommended_provider: str
    readiness_score: int
    complexity: str
    approval_status: ApprovalStatus


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    assessment_id: str
    message: str
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str

class MigrationStrategyResult(BaseModel):
    strategy: str
    confidence: str
    reasons: list[str]

