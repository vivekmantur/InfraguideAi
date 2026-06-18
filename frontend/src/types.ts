export type Requirements = {
  cloud_provider: string;
  migration_goal: string;
  expected_traffic: string;
  budget_preference: string;
  migration_timeline: string;
};

export type SourceMode = "github" | "folder";

export type FieldErrors = Partial<Record<keyof Requirements | "repositoryUrl" | "projectFolder", string>>;

export type ServiceRecommendation = {
  component: string;
  current: string;
  recommended: string;
};

export type RegionalServicePrice = {
  component: string;
  recommended?: string;
  currency?: string;
  monthly_cost: number;
  source?: string;
};

export type RegionalPrice = {
  provider?: string;
  region: string;
  currency: string;
  runtime_sku?: string;
  runtime_monthly: number;
  services_monthly: number;
  service_breakdown?: RegionalServicePrice[];
  total_monthly: number;
  source?: string;
};

export type Assessment = {
  technology_stack: {
    project_summary?: string;
    languages?: string[];
    frameworks?: string[];
    runtimes?: string[];
    hosting_model?: string;
    deployment_model?: string;
    triggers?: string[];
    databases?: string[];
    package_managers?: string[];
    container_configs?: string[];
    cloud_dependencies?: string[];
    dependency_graph?: string[];
    architecture_pattern: string;
  };
  architecture_summary: string;
  cloud_readiness: {
    score: number;
    complexity: string;
    runtime_compatibility: string;
    database_compatibility: string;
    container_readiness: string;
    configuration_readiness: string;
    findings?: string[];
    score_breakdown?: string[];
  };
  recommended_provider: string;
  recommended_services: ServiceRecommendation[];
  cost_estimation: {
    currency: string;
    monthly: number;
    monthly_range?: string;
    annual: number;
    line_items?: string[];
    assumptions?: string[];
    regional_prices?: RegionalPrice[];
  };
  cloud_sizing?: {
    cpu_cores?: number;
    memory_gb?: number;
  } | null;
  governance_assessment?: {
    risk_level: string;
    issues?: string[];
    passed_checks?: string[];
    recommendations?: string[];
    recommendation: string;
  };
  modernization_opportunities: string[];
  migration_strategy: string;
  migration_roadmap: string[];
  blueprint_markdown: string;
  warnings: string[];
};

export type ServiceAvailabilityResult = {
  provider: string;
  region: string;
  catalog_source?: string;
  catalog_version?: string;
  region_supported: boolean;
  available: Array<{
    component?: string;
    service: string;
    category: string;
  }>;
  unavailable: Array<{
    component?: string;
    service: string;
    category: string;
  }>;
  notes: string[];
};

export type RuntimeSupportResult = {
  provider: string;
  target_service: string;
  catalog_source?: string;
  catalog_version?: string;
  supported: boolean;
  supported_runtimes: string[];
  unsupported_runtimes: string[];
  catalog_supported_runtimes: string[];
  notes: string[];
};
