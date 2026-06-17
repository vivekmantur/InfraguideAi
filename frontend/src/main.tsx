import React from "react";
import ReactDOM from "react-dom/client";
import { ArrowDownToLine, CloudCog, FileText, FolderOpen, GitBranch, Loader2, Route, ServerCog, X } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:9000";
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const IGNORED_UPLOAD_PARTS = new Set([".git", "node_modules", "vendor", "bin", "obj", "dist", "build", ".venv", "venv", "env", "__pycache__"]);

type Requirements = {
  cloud_provider: string;
  migration_goal: string;
  expected_traffic: string;
  budget_preference: string;
  migration_timeline: string;
};

type SourceMode = "github" | "folder";

type ServiceRecommendation = {
  component: string;
  current: string;
  recommended: string;
};

type RegionalPrice = {
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

type RegionalServicePrice = {
  component: string;
  recommended?: string;
  currency?: string;
  monthly_cost: number;
  source?: string;
};

type Assessment = {
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

const options = {
  cloud_provider: ["AWS", "Azure", "GCP"],
  migration_goal: ["Application Modernization", "Cost Optimization", "Lift-and-Shift", "Scalability", "Performance Improvement"],
  expected_traffic: ["Low", "Medium", "High"],
  budget_preference: ["Balanced", "Low Cost", "Performance Focused"],
  migration_timeline: ["3 Months", "Immediate", "6 Months", "Flexible"],
};

const requiredFieldMessage = "Required field missing";

const emptyRequirements = (): Requirements => ({
  cloud_provider: "",
  migration_goal: "",
  expected_traffic: "",
  budget_preference: "",
  migration_timeline: "",
});

const pricingRegions: Record<string, string[]> = {
  AWS: [
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
  ],
  Azure: [
    "eastus",
    "eastus2",
    "centralus",
    "westus",
    "westus2",
    "westus3",
    "southcentralus",
    "northeurope",
    "westeurope",
    "uksouth",
    "germanywestcentral",
    "francecentral",
    "switzerlandnorth",
    "canadacentral",
    "brazilsouth",
    "centralindia",
    "southindia",
    "southeastasia",
    "eastasia",
    "japaneast",
    "koreacentral",
    "australiaeast",
  ],
  GCP: [
    "us-central1",
    "us-east1",
    "us-east4",
    "us-west1",
    "us-west2",
    "northamerica-northeast1",
    "southamerica-east1",
    "europe-west1",
    "europe-west2",
    "europe-west3",
    "europe-west4",
    "europe-north1",
    "asia-south1",
    "asia-east1",
    "asia-east2",
    "asia-northeast1",
    "asia-southeast1",
    "australia-southeast1",
  ],
};

function App() {
  const [sourceMode, setSourceMode] = React.useState<SourceMode>("github");
  const [repositoryUrl, setRepositoryUrl] = React.useState("");
  const [githubToken, setGithubToken] = React.useState("");
  const [selectedFiles, setSelectedFiles] = React.useState<File[]>([]);
  const folderInputRef = React.useRef<HTMLInputElement | null>(null);
  const [githubRequirements, setGithubRequirements] = React.useState<Requirements>(emptyRequirements);
  const [folderRequirements, setFolderRequirements] = React.useState<Requirements>(emptyRequirements);
  const [fieldErrors, setFieldErrors] = React.useState<Partial<Record<keyof Requirements | "repositoryUrl" | "projectFolder", string>>>({});
  const [assessment, setAssessment] = React.useState<Assessment | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isTokenModalOpen, setIsTokenModalOpen] = React.useState(false);
  const [error, setError] = React.useState("");
  const requirements = sourceMode === "github" ? githubRequirements : folderRequirements;

  async function submitAssessment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateMigrationInput();

    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setError("");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = sourceMode === "github" ? await submitGithubAssessment() : await submitFolderAssessment();

      if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
      }

      const nextAssessment = await response.json() as Assessment;
      if (sourceMode === "github" && !githubToken.trim() && hasRepositoryCloneFailure(nextAssessment)) {
        setAssessment(null);
        setIsTokenModalOpen(true);
        return;
      }
      if (sourceMode === "github" && githubToken.trim() && hasRepositoryCloneFailure(nextAssessment)) {
        throw new Error("GitHub clone failed. Check that the repository URL is correct and the access token has read access.");
      }

      setAssessment(nextAssessment);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Assessment failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function submitGithubAssessment(tokenOverride = githubToken) {
    const trimmedUrl = repositoryUrl.trim();
    if (!trimmedUrl) {
      throw new Error("Enter a GitHub repository URL before generating a blueprint.");
    }
    if (!/^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/.test(trimmedUrl)) {
      throw new Error("Enter a valid GitHub repository URL, for example https://github.com/owner/repository.");
    }

    return fetch(`${API_BASE_URL}/assessments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repository_url: trimmedUrl,
        github_token: tokenOverride.trim() || undefined,
        requirements,
      }),
    });
  }

  async function submitPrivateRepositoryToken(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = githubToken.trim();
    if (!token) {
      setError("Enter a GitHub access token to analyze this private repository.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await submitGithubAssessment(token);
      if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
      }

      const nextAssessment = await response.json() as Assessment;
      if (hasRepositoryCloneFailure(nextAssessment)) {
        throw new Error("GitHub clone failed. Check that the access token has read access to this repository.");
      }

      setAssessment(nextAssessment);
      setIsTokenModalOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Private repository assessment failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function submitFolderAssessment() {
    if (selectedFiles.length === 0) {
      throw new Error("Select a project folder before generating a blueprint.");
    }

    const uploadFiles = analyzableFiles(selectedFiles);
    if (uploadFiles.length === 0) {
      throw new Error("No analyzable files found. Choose the project source folder, not only dependency or build output folders.");
    }
    const totalBytes = uploadFiles.reduce((sum, file) => sum + file.size, 0);
    if (totalBytes > MAX_UPLOAD_BYTES) {
      throw new Error("Uploaded source files are too large for this MVP scan.");
    }

    const formData = new FormData();
    formData.append("requirements", JSON.stringify(requirements));
    formData.append("project_name", uploadFiles[0].webkitRelativePath?.split("/")[0] || "Uploaded folder");
    for (const file of uploadFiles) {
      formData.append("files", file, file.webkitRelativePath || file.name);
    }

    return fetch(`${API_BASE_URL}/assessments/upload`, {
      method: "POST",
      body: formData,
    });
  }

  function updateRequirement(key: keyof Requirements, value: string) {
    const update = (current: Requirements) => ({ ...current, [key]: value });

    if (sourceMode === "github") {
      setGithubRequirements(update);
    } else {
      setFolderRequirements(update);
    }

    setFieldErrors((current) => ({ ...current, [key]: value ? "" : requiredFieldMessage }));
  }

  function switchSourceMode(mode: SourceMode) {
    setSourceMode(mode);
    setFieldErrors({});
    setError("");
  }

  function clearSelectedFolder() {
    setSelectedFiles([]);
    setFieldErrors((current) => ({ ...current, projectFolder: requiredFieldMessage }));
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
  }

  function validateMigrationInput() {
    const errors: Partial<Record<keyof Requirements | "repositoryUrl" | "projectFolder", string>> = {};

    if (sourceMode === "github" && !repositoryUrl.trim()) {
      errors.repositoryUrl = requiredFieldMessage;
    }

    if (sourceMode === "folder" && selectedFiles.length === 0) {
      errors.projectFolder = requiredFieldMessage;
    }

    (Object.keys(requirements) as Array<keyof Requirements>).forEach((key) => {
      if (!requirements[key]) {
        errors[key] = requiredFieldMessage;
      }
    });

    return errors;
  }

  const uploadableFiles = React.useMemo(() => analyzableFiles(selectedFiles), [selectedFiles]);

  function downloadBlueprint() {
    if (!assessment) return;
    const blob = new Blob([assessment.blueprint_markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "infraguide-ai-migration-blueprint.md";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen bg-cloud text-ink">
      <section className="border-b border-ink/10 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-moss">
              <CloudCog size={18} />
              Cloud Migration Intelligence Platform
            </div>
            <h1 className="text-4xl font-bold tracking-normal sm:text-5xl">InfraGuide AI</h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-ink/70">
              Analyze application repositories, evaluate cloud readiness, map services, estimate costs, and generate a practical migration roadmap.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <Metric label="Readiness" value={assessment ? `${assessment.cloud_readiness.score}%` : "--"} />
            <Metric label="Provider" value={assessment?.recommended_provider ?? "--"} />
            <Metric label="Strategy" value={assessment?.migration_strategy ?? "--"} />
          </div>
        </div>
      </section>

      <section className="grid w-full items-start gap-5 px-5 py-5 lg:grid-cols-[420px_minmax(0,1fr)] xl:grid-cols-[420px_minmax(0,1fr)_420px]">
        <form onSubmit={submitAssessment} className="rounded-lg border border-ink/10 bg-white p-5 shadow-panel lg:sticky lg:top-5 lg:max-h-[calc(100vh-2.5rem)] lg:overflow-auto">
          <div className="mb-5 flex items-center gap-2">
            {sourceMode === "github" ? <GitBranch size={20} className="text-signal" /> : <FolderOpen size={20} className="text-signal" />}
            <h2 className="text-xl font-semibold">Migration Input</h2>
          </div>

          <div className="mb-5 grid grid-cols-2 rounded-md border border-ink/10 bg-cloud p-1">
            <button type="button" className={`source-tab ${sourceMode === "github" ? "source-tab-active" : ""}`} onClick={() => switchSourceMode("github")}>
              GitHub URL
            </button>
            <button type="button" className={`source-tab ${sourceMode === "folder" ? "source-tab-active" : ""}`} onClick={() => switchSourceMode("folder")}>
              Upload Folder
            </button>
          </div>

          {sourceMode === "github" ? (
            <>
              <RequiredLabel htmlFor="repositoryUrl">GitHub Repository</RequiredLabel>
              <input
                id="repositoryUrl"
                className={`input ${fieldErrors.repositoryUrl ? "input-error" : ""}`}
                value={repositoryUrl}
                onChange={(event) => {
                  setRepositoryUrl(event.target.value);
                  setFieldErrors((current) => ({ ...current, repositoryUrl: event.target.value.trim() ? "" : requiredFieldMessage }));
                }}
                placeholder="https://github.com/company/ecommerce-app"
              />
              {fieldErrors.repositoryUrl && <FieldError message={fieldErrors.repositoryUrl} />}
            </>
          ) : (
            <label>
              <RequiredLabel>Project Folder</RequiredLabel>
              <input
                ref={folderInputRef}
                className={`input file-input ${fieldErrors.projectFolder ? "input-error" : ""}`}
                type="file"
                multiple
                onChange={(event) => {
                  const files = Array.from(event.target.files ?? []);
                  setSelectedFiles(files);
                  setFieldErrors((current) => ({ ...current, projectFolder: files.length > 0 ? "" : requiredFieldMessage }));
                }}
                {...{ webkitdirectory: "", directory: "" }}
              />
              {selectedFiles.length > 0 ? (
                <span className="mt-2 flex items-center justify-between gap-3 rounded-md bg-cloud px-3 py-2 text-sm text-ink/70">
                  <span>
                    {selectedFiles.length} files selected, {uploadableFiles.length} source/config files will be analyzed from {selectedFiles[0].webkitRelativePath?.split("/")[0] || "folder"}.
                  </span>
                  <button type="button" className="clear-folder-button" onClick={clearSelectedFolder} aria-label="Remove selected folder">
                    <X size={16} />
                  </button>
                </span>
              ) : (
                <span className="mt-2 block text-sm text-ink/60">Choose a local project folder to scan.</span>
              )}
              {fieldErrors.projectFolder && <FieldError message={fieldErrors.projectFolder} />}
            </label>
          )}

          <div className="mt-5 grid gap-4">
            <Select label="Cloud Provider" value={requirements.cloud_provider} values={options.cloud_provider} placeholder="Select cloud provider" error={fieldErrors.cloud_provider} onChange={(value) => updateRequirement("cloud_provider", value)} />
            <Select label="Migration Goal" value={requirements.migration_goal} values={options.migration_goal} placeholder="Select migration goal" error={fieldErrors.migration_goal} onChange={(value) => updateRequirement("migration_goal", value)} />
            <Select label="Expected Traffic" value={requirements.expected_traffic} values={options.expected_traffic} placeholder="Select expected traffic" error={fieldErrors.expected_traffic} onChange={(value) => updateRequirement("expected_traffic", value)} />
            <Select label="Budget Preference" value={requirements.budget_preference} values={options.budget_preference} placeholder="Select budget preference" error={fieldErrors.budget_preference} onChange={(value) => updateRequirement("budget_preference", value)} />
            <Select label="Migration Timeline" value={requirements.migration_timeline} values={options.migration_timeline} placeholder="Select migration timeline" error={fieldErrors.migration_timeline} onChange={(value) => updateRequirement("migration_timeline", value)} />
          </div>

          <button className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-moss px-4 py-3 font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-60" disabled={isLoading}>
            {isLoading ? <Loader2 className="animate-spin" size={18} /> : <ServerCog size={18} />}
            Generate Blueprint
          </button>

          {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </form>

        <section className="min-h-[680px] rounded-lg border border-ink/10 bg-white p-5 shadow-panel">
          {assessment ? (
            <Report assessment={assessment} onDownload={downloadBlueprint} />
          ) : (
            <div className="flex h-full min-h-[520px] flex-col items-center justify-center text-center">
              <Route size={44} className="mb-4 text-signal" />
              <h2 className="text-2xl font-semibold">Migration blueprint output</h2>
              <p className="mt-3 max-w-xl text-ink/65">
                Submit a repository and migration profile to generate stack analysis, readiness scoring, service mapping, strategy, cost estimate, and roadmap.
              </p>
            </div>
          )}
        </section>

        <BlueprintPreview assessment={assessment} className="lg:col-span-2 xl:col-span-1" />
      </section>

      {isTokenModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="privateRepoTitle">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 id="privateRepoTitle" className="text-xl font-semibold">Private GitHub Repository</h2>
                <p className="mt-2 text-sm leading-6 text-ink/70">
                  This GitHub URL is private or cannot be accessed publicly. Please provide an access token to continue.
                </p>
              </div>
              <button type="button" className="clear-folder-button" onClick={() => setIsTokenModalOpen(false)} aria-label="Close access token dialog">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={submitPrivateRepositoryToken}>
              <label htmlFor="modalGithubToken">
                <span className="field-label">Access Token</span>
                <input
                  id="modalGithubToken"
                  className="input"
                  value={githubToken}
                  onChange={(event) => setGithubToken(event.target.value)}
                  placeholder="Paste GitHub access token"
                  type="password"
                  autoComplete="off"
                />
              </label>

              <div className="mt-4 rounded-md bg-cloud p-3 text-xs leading-5 text-ink/65">
                <p className="font-semibold text-ink/75">Steps to get an access token:</p>
                <ol className="mt-2 list-decimal space-y-1 pl-4">
                  <li>Open GitHub Settings, then Developer settings.</li>
                  <li>Go to Personal access tokens and create a fine-grained token.</li>
                  <li>Select the private repository you want to analyze.</li>
                  <li>Give read-only access to repository contents and metadata.</li>
                  <li>Generate the token, copy it, and paste it here.</li>
                </ol>
              </div>

              {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
                <button type="button" className="rounded-md border border-ink/15 px-4 py-2 font-semibold text-ink/70 transition hover:bg-cloud" onClick={() => setIsTokenModalOpen(false)}>
                  Cancel
                </button>
                <button className="flex items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-60" disabled={isLoading || !githubToken.trim()}>
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : <GitBranch size={18} />}
                  Submit Token
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-28 rounded-md border border-ink/10 bg-cloud px-4 py-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-ink/55">{label}</div>
      <div className="mt-1 text-lg font-bold text-ink">{value}</div>
    </div>
  );
}

function RequiredLabel({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <span className="field-label" {...(htmlFor ? { id: `${htmlFor}Label` } : {})}>
      {children}
      <span className="required-star" aria-hidden="true">*</span>
    </span>
  );
}

function FieldError({ message }: { message: string }) {
  return (
    <span className="field-error">{message}</span>
  );
}

function Select({
  label,
  value,
  values,
  placeholder,
  error,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  placeholder: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <RequiredLabel>{label}</RequiredLabel>
      <select className={`input ${error ? "input-error" : ""}`} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="" disabled>{placeholder}</option>
        {values.map((item) => (
          <option key={item} value={item}>{item}</option>
        ))}
      </select>
      {error && <FieldError message={error} />}
    </label>
  );
}

function Report({ assessment, onDownload }: { assessment: Assessment; onDownload: () => void }) {
  const [isPricingModalOpen, setIsPricingModalOpen] = React.useState(false);
  const [appliedRegionalPrice, setAppliedRegionalPrice] = React.useState<RegionalPrice | null>(null);
  const governance = assessment.governance_assessment ?? {
    risk_level: "Not assessed",
    issues: [],
    passed_checks: [],
    recommendations: [],
    recommendation: "Security and governance assessment was not returned by the API.",
  };
  const activeMonthlyValue = appliedRegionalPrice
    ? formatMoney(appliedRegionalPrice.currency, appliedRegionalPrice.total_monthly)
    : formatMoney(assessment.cost_estimation.currency, assessment.cost_estimation.monthly);
  const activeAnnualValue = appliedRegionalPrice
    ? formatMoney(appliedRegionalPrice.currency, appliedRegionalPrice.total_monthly * 12)
    : formatMoney(assessment.cost_estimation.currency, assessment.cost_estimation.annual);
  const activeRangeValue = appliedRegionalPrice
    ? `${appliedRegionalPrice.region} selected`
    : assessment.cost_estimation.monthly_range ?? "Not estimated";
  const activeLineItems = appliedRegionalPrice
    ? [
        `${appliedRegionalPrice.runtime_sku || "Runtime"} in ${appliedRegionalPrice.region}: ${formatMoney(appliedRegionalPrice.currency, appliedRegionalPrice.runtime_monthly)}/month`,
        ...((appliedRegionalPrice.service_breakdown ?? []).map((service) => (
          `${service.component}: ${service.recommended ?? "Managed service"}: ${formatMoney(service.currency ?? appliedRegionalPrice.currency, service.monthly_cost)}/month`
        ))),
      ]
    : assessment.cost_estimation.line_items;

  return (
    <div>
      <div className="mb-5 flex flex-col gap-3 border-b border-ink/10 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Migration Blueprint</h2>
          <p className="mt-1 text-sm text-ink/65">{assessment.architecture_summary}</p>
        </div>
        <button onClick={onDownload} className="flex items-center justify-center gap-2 rounded-md border border-moss px-4 py-2 font-semibold text-moss transition hover:bg-moss hover:text-white">
          <ArrowDownToLine size={18} />
          Markdown
        </button>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Technology Stack">
          <KeyValue label="Languages" value={list(assessment.technology_stack.languages)} />
          <KeyValue label="Summary" value={assessment.technology_stack.project_summary ?? assessment.architecture_summary} />
          <KeyValue label="Frameworks" value={list(assessment.technology_stack.frameworks)} />
          <KeyValue label="Runtime" value={list(assessment.technology_stack.runtimes)} />
          <KeyValue label="Hosting" value={assessment.technology_stack.hosting_model ?? "Not detected"} />
          <KeyValue label="Deployment" value={assessment.technology_stack.deployment_model ?? "Not detected"} />
          <KeyValue label="Triggers" value={list(assessment.technology_stack.triggers)} />
          <KeyValue label="Databases" value={list(assessment.technology_stack.databases)} />
          <KeyValue label="Containers" value={list(assessment.technology_stack.container_configs)} />
        </Panel>

        <Panel title="Cloud Readiness">
          <div className="mb-4 h-3 rounded-full bg-cloud">
            <div className="h-3 rounded-full bg-signal" style={{ width: `${assessment.cloud_readiness.score}%` }} />
          </div>
          <KeyValue label="Score" value={`${assessment.cloud_readiness.score}%`} />
          <KeyValue label="Complexity" value={assessment.cloud_readiness.complexity} />
          <KeyValue label="Container" value={assessment.cloud_readiness.container_readiness} />
          <KeyValue label="Configuration" value={assessment.cloud_readiness.configuration_readiness} />
          <div className="mt-4">
            <List items={assessment.cloud_readiness.score_breakdown} />
          </div>
        </Panel>

        <Panel title="Recommended Services">
          <div className="space-y-3">
            {assessment.recommended_services.map((item) => (
              <div key={item.component} className="rounded-md bg-cloud p-3">
                <div className="font-semibold">{item.component}</div>
                <div className="mt-1 text-sm text-ink/65">{item.current} {"->"} {item.recommended}</div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Cost And Strategy"
          action={
            <button
              type="button"
              className="rounded-md border border-moss px-3 py-1.5 text-sm font-semibold text-moss transition hover:bg-moss hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => setIsPricingModalOpen(true)}
            >
              View more
            </button>
          }
        >
          <KeyValue label="Provider" value={assessment.recommended_provider} />
          <KeyValue label="Strategy" value={assessment.migration_strategy} />
          <KeyValue label="Location" value={appliedRegionalPrice?.region ?? "Default estimate"} />
          <KeyValue label="Monthly" value={activeMonthlyValue} />
          <KeyValue label="Range" value={activeRangeValue} />
          <KeyValue label="Annual" value={activeAnnualValue} />
          <div className="mt-4">
            <List items={activeLineItems} />
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Panel title="Dependencies">
          <KeyValue label="Cloud" value={list(assessment.technology_stack.cloud_dependencies)} />
          <List items={assessment.technology_stack.dependency_graph} />
        </Panel>
        <Panel title="Security">
          <KeyValue label="Risk" value={governance.risk_level} />
          <List items={[...(governance.passed_checks ?? []), ...(governance.issues ?? []), ...(governance.recommendations ?? [])]} />
        </Panel>
        <Panel title="Modernization">
          <List items={assessment.modernization_opportunities} />
        </Panel>
        <Panel title="Roadmap">
          <List items={assessment.migration_roadmap} numbered />
        </Panel>
      </div>

      {assessment.warnings.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {assessment.warnings.join(" ")}
        </div>
      )}

      {isPricingModalOpen && (
        <RegionalPricingModal
          provider={assessment.recommended_provider}
          initialPrices={assessment.cost_estimation.regional_prices ?? []}
          cloudSizing={assessment.cloud_sizing}
          services={assessment.recommended_services}
          appliedRegion={appliedRegionalPrice}
          onApply={(price) => {
            setAppliedRegionalPrice(price);
            setIsPricingModalOpen(false);
          }}
          onClose={() => setIsPricingModalOpen(false)}
        />
      )}
    </div>
  );
}

function BlueprintPreview({ assessment, className = "" }: { assessment: Assessment | null; className?: string }) {
  return (
    <aside className={`min-h-[680px] rounded-lg border border-ink/10 bg-white p-5 shadow-panel lg:sticky lg:top-5 lg:max-h-[calc(100vh-2.5rem)] ${className}`}>
      <div className="mb-4 flex items-center gap-2">
        <FileText size={20} className="text-signal" />
        <h2 className="text-xl font-semibold">Blueprint Preview</h2>
      </div>
      {assessment ? (
        <pre className="max-h-[calc(100vh-7.5rem)] min-h-[580px] overflow-auto whitespace-pre-wrap rounded-md bg-ink p-4 text-sm leading-6 text-white">
          {assessment.blueprint_markdown}
        </pre>
      ) : (
        <div className="flex min-h-[580px] flex-col justify-center rounded-md bg-cloud p-4 text-center text-sm leading-6 text-ink/65">
          Markdown preview appears here after a blueprint is generated.
        </div>
      )}
    </aside>
  );
}

function RegionalPricingModal({
  provider,
  initialPrices,
  cloudSizing,
  services,
  appliedRegion,
  onApply,
  onClose,
}: {
  provider: string;
  initialPrices: RegionalPrice[];
  cloudSizing?: { cpu_cores?: number; memory_gb?: number } | null;
  services: ServiceRecommendation[];
  appliedRegion: RegionalPrice | null;
  onApply: (price: RegionalPrice) => void;
  onClose: () => void;
}) {
  const [prices, setPrices] = React.useState<RegionalPrice[]>(initialPrices);
  const [selectedRegion, setSelectedRegion] = React.useState<RegionalPrice | null>(appliedRegion ?? initialPrices[0] ?? null);
  const [isLoadingRegions, setIsLoadingRegions] = React.useState(initialPrices.length === 0 && ["Azure", "GCP"].includes(provider));
  const [regionalError, setRegionalError] = React.useState("");
  const [selectedPricingRegion, setSelectedPricingRegion] = React.useState("");
  const [hasLoadedRegionList, setHasLoadedRegionList] = React.useState(initialPrices.length > 0);
  const availableRegions = pricingRegions[provider] ?? [];

  React.useEffect(() => {
    if (provider === "AWS") {
      const rows = selectedPricingRegion
        ? initialPrices.filter((price) => price.region === selectedPricingRegion)
        : initialPrices.slice(0, 10);

      setPrices(rows);
      setSelectedRegion((current) => rows.find((row) => row.region === current?.region) ?? rows[0] ?? null);
      setHasLoadedRegionList(initialPrices.length > 0);
      setRegionalError("");
      setIsLoadingRegions(false);
      return;
    }

    if (!["Azure", "GCP"].includes(provider)) {
      return;
    }

    let isActive = true;

    async function loadRegionalPricing() {
      setIsLoadingRegions(true);
      setRegionalError("");

      try {
        const response = await fetch(`${API_BASE_URL}/pricing/regions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider,
            cpu: cloudSizing?.cpu_cores ?? 2,
            memory: cloudSizing?.memory_gb ?? 4,
            limit: selectedPricingRegion ? 1 : 10,
            region: selectedPricingRegion || undefined,
            services: services
              .filter((service) => service.component !== "Application Runtime")
              .map((service) => ({
                component: service.component,
                recommended: service.recommended,
                current: service.current,
              })),
          }),
        });

        if (!response.ok) {
          throw new Error(await responseErrorMessage(response));
        }

        const data = await response.json();
        const rows = data.regions ?? [];

        if (isActive) {
          setPrices(rows);
          setSelectedRegion((current) => rows.find((row: RegionalPrice) => row.region === current?.region) ?? rows[0] ?? null);
          if (!selectedPricingRegion && rows.length > 0) {
            setHasLoadedRegionList(true);
          }
        }
      } catch (caught) {
        if (isActive) {
          setRegionalError(caught instanceof Error ? caught.message : "Regional pricing failed");
        }
      } finally {
        if (isActive) {
          setIsLoadingRegions(false);
        }
      }
    }

    loadRegionalPricing();

    return () => {
      isActive = false;
    };
  }, [cloudSizing?.cpu_cores, cloudSizing?.memory_gb, initialPrices, provider, selectedPricingRegion, services]);

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel regional-pricing-modal" role="dialog" aria-modal="true" aria-labelledby="regionalPricingTitle">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
            <h2 id="regionalPricingTitle" className="text-xl font-semibold">{provider} regional pricing</h2>
            <p className="mt-1 text-sm text-ink/65">Monthly estimate by region for runtime and recommended services.</p>
            </div>
            {availableRegions.length > 0 && (
              <label className="w-full sm:w-64">
                <span className="field-label">Location</span>
                <select
                  className="input"
                  value={selectedPricingRegion}
                  onChange={(event) => setSelectedPricingRegion(event.target.value)}
                  disabled={!hasLoadedRegionList || isLoadingRegions}
                >
                  <option value="">Top 10 regions</option>
                  {availableRegions.map((region) => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <button type="button" className="clear-folder-button" onClick={onClose} aria-label="Close regional pricing dialog">
            <X size={16} />
          </button>
        </div>

        {isLoadingRegions ? (
          <div className="rounded-md border border-ink/10 bg-cloud p-4 text-sm leading-6 text-ink/70">
            Loading regional pricing from {provider}. This can take a little longer for GCP because Google Billing pricing is paged by service and SKU.
          </div>
        ) : regionalError ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">
            {regionalError}
          </div>
        ) : prices.length > 0 ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
            <div className="overflow-x-hidden overflow-y-auto rounded-md border border-ink/10">
              <table className="w-full table-fixed border-collapse text-left text-sm">
                <thead className="bg-cloud text-xs uppercase text-ink/60">
                  <tr>
                    <th className="w-[23%] px-3 py-3 font-bold">Region</th>
                    <th className="w-[20%] px-3 py-3 font-bold">Runtime SKU</th>
                    <th className="w-[14%] px-3 py-3 text-right font-bold">Runtime</th>
                    <th className="w-[16%] px-3 py-3 text-right font-bold">Services Total</th>
                    <th className="w-[14%] px-3 py-3 text-right font-bold">Total</th>
                    <th className="w-[13%] px-3 py-3 font-bold">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.map((price) => {
                    const isSelected = selectedRegion?.region === price.region;

                    return (
                      <tr
                        key={`${price.provider ?? provider}-${price.region}`}
                        className={`cursor-pointer border-t border-ink/10 transition hover:bg-cloud ${isSelected ? "bg-cloud" : ""}`}
                        onClick={() => setSelectedRegion(price)}
                      >
                        <td className="break-words px-3 py-3 font-semibold text-moss">{price.region}</td>
                        <td className="break-words px-3 py-3 text-ink/70">{price.runtime_sku || "Runtime"}</td>
                        <td className="px-3 py-3 text-right">{formatMoney(price.currency, price.runtime_monthly)}</td>
                        <td className="px-3 py-3 text-right">{formatMoney(price.currency, price.services_monthly)}</td>
                        <td className="px-3 py-3 text-right font-bold">{formatMoney(price.currency, price.total_monthly)}</td>
                        <td className="break-words px-3 py-3 text-ink/65">{price.source ?? "Pricing API"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <RegionServiceBreakdown
              price={selectedRegion}
              appliedRegion={appliedRegion}
              onApply={onApply}
            />
          </div>
        ) : (
          <div className="rounded-md border border-ink/10 bg-cloud p-4 text-sm leading-6 text-ink/70">
            Regional pricing rows were not returned for this assessment. Regenerate the blueprint after restarting the backend, MCP server, and bridge so the latest regional pricing endpoints are active.
          </div>
        )}
      </section>
    </div>
  );
}

function RegionServiceBreakdown({
  price,
  appliedRegion,
  onApply,
}: {
  price: RegionalPrice | null;
  appliedRegion: RegionalPrice | null;
  onApply: (price: RegionalPrice) => void;
}) {
  if (!price) {
    return (
      <aside className="rounded-md border border-ink/10 bg-cloud p-4 text-sm text-ink/65">
        Select a region to view service costs.
      </aside>
    );
  }

  return (
    <aside className="rounded-md border border-ink/10 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{price.region}</h3>
        <p className="mt-1 text-sm text-ink/65">Service cost breakdown for this region.</p>
      </div>

      <KeyValue label="Runtime" value={formatMoney(price.currency, price.runtime_monthly)} />
      <KeyValue label="Services Total" value={formatMoney(price.currency, price.services_monthly)} />
      <KeyValue label="Total" value={formatMoney(price.currency, price.total_monthly)} />
      <div className="mt-4">
        <button
          type="button"
          className="flex w-full items-center justify-center rounded-md bg-moss px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => onApply(price)}
          disabled={appliedRegion?.region === price.region && appliedRegion.total_monthly === price.total_monthly}
        >
          {appliedRegion?.region === price.region && appliedRegion.total_monthly === price.total_monthly
            ? "Migration location updated"
            : "Update location to migration"}
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {(price.service_breakdown ?? []).length > 0 ? (
          price.service_breakdown?.map((service) => (
            <div key={`${price.region}-${service.component}`} className="rounded-md bg-cloud p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold">{service.component}</div>
                  {service.recommended && (
                    <div className="mt-1 text-xs leading-5 text-ink/60">{service.recommended}</div>
                  )}
                </div>
                <div className="text-right font-bold">
                  {formatMoney(service.currency ?? price.currency, service.monthly_cost)}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-md bg-cloud p-3 text-sm leading-6 text-ink/65">
            Per-service rows were not returned for this region. Regenerate the assessment after restarting MCP and bridge so the latest service breakdown response is active.
          </div>
        )}
      </div>
    </aside>
  );
}

function Panel({ title, children, className = "", action }: { title: string; children: React.ReactNode; className?: string; action?: React.ReactNode }) {
  return (
    <section className={`rounded-lg border border-ink/10 p-4 ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-lg font-semibold">
          <FileText size={18} className="text-signal" />
          {title}
        </h3>
        {action}
      </div>
      {children}
    </section>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-3 flex items-start justify-between gap-4 border-b border-ink/10 pb-2 last:mb-0 last:border-0 last:pb-0">
      <span className="text-sm font-semibold text-ink/60">{label}</span>
      <span className="max-w-[65%] text-right text-sm font-semibold">{value}</span>
    </div>
  );
}

function List({ items = [], numbered = false }: { items?: string[]; numbered?: boolean }) {
  const ListTag = numbered ? "ol" : "ul";
  return (
    <ListTag className={`space-y-2 text-sm leading-6 text-ink/75 ${numbered ? "list-decimal pl-5" : "list-disc pl-5"}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ListTag>
  );
}

function list(items?: string[]) {
  return items?.length ? items.join(", ") : "Not detected";
}

function formatMoney(currency: string, amount: number) {
  return `${currency} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function analyzableFiles(files: File[]) {
  return files.filter((file) => {
    const path = file.webkitRelativePath || file.name;
    const parts = path.split(/[\\/]/);
    return !parts.some((part) => IGNORED_UPLOAD_PARTS.has(part));
  });
}

function hasRepositoryCloneFailure(assessment: Assessment) {
  return assessment.warnings?.some((warning) => warning.toLowerCase().startsWith("repository clone failed:")) ?? false;
}

async function responseErrorMessage(response: Response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    // Fall through to the generic status message.
  }
  return `Assessment failed with status ${response.status}`;
}

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: string }> {
  state = { error: "" };

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : "The interface could not render this response." };
  }

  render() {
    if (this.state.error) {
      return (
        <main className="min-h-screen bg-cloud p-6 text-ink">
          <section className="mx-auto max-w-3xl rounded-lg border border-red-200 bg-white p-5 shadow-panel">
            <h1 className="text-2xl font-semibold text-red-700">InfraGuide AI could not render the report</h1>
            <p className="mt-3 text-ink/70">{this.state.error}</p>
            <p className="mt-3 text-sm text-ink/60">Restart the frontend and backend after code changes, then generate the blueprint again.</p>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
