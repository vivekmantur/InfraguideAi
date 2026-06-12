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

type ServiceRecommendation = {
  component: string;
  current: string;
  recommended: string;
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
    monthly: number;
    monthly_range?: string;
    annual: number;
    line_items?: string[];
    assumptions?: string[];
  };
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
  cloud_provider: ["No Preference", "AWS", "Azure", "GCP"],
  migration_goal: ["Application Modernization", "Cost Optimization", "Lift-and-Shift", "Scalability", "Performance Improvement"],
  expected_traffic: ["Low", "Medium", "High"],
  budget_preference: ["Balanced", "Low Cost", "Performance Focused"],
  migration_timeline: ["3 Months", "Immediate", "6 Months", "Flexible"],
};

function App() {
  const [sourceMode, setSourceMode] = React.useState<"github" | "folder">("github");
  const [repositoryUrl, setRepositoryUrl] = React.useState("");
  const [githubToken, setGithubToken] = React.useState("");
  const [selectedFiles, setSelectedFiles] = React.useState<File[]>([]);
  const folderInputRef = React.useRef<HTMLInputElement | null>(null);
  const [requirements, setRequirements] = React.useState<Requirements>({
    cloud_provider: "No Preference",
    migration_goal: "Application Modernization",
    expected_traffic: "Medium",
    budget_preference: "Balanced",
    migration_timeline: "3 Months",
  });
  const [assessment, setAssessment] = React.useState<Assessment | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isTokenModalOpen, setIsTokenModalOpen] = React.useState(false);
  const [error, setError] = React.useState("");

  async function submitAssessment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
    setRequirements((current) => ({ ...current, [key]: value }));
  }

  function clearSelectedFolder() {
    setSelectedFiles([]);
    if (folderInputRef.current) {
      folderInputRef.current.value = "";
    }
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
            <button type="button" className={`source-tab ${sourceMode === "github" ? "source-tab-active" : ""}`} onClick={() => setSourceMode("github")}>
              GitHub URL
            </button>
            <button type="button" className={`source-tab ${sourceMode === "folder" ? "source-tab-active" : ""}`} onClick={() => setSourceMode("folder")}>
              Upload Folder
            </button>
          </div>

          {sourceMode === "github" ? (
            <>
              <label className="field-label" htmlFor="repositoryUrl">GitHub Repository</label>
              <input
                id="repositoryUrl"
                className="input"
                value={repositoryUrl}
                onChange={(event) => setRepositoryUrl(event.target.value)}
                placeholder="https://github.com/company/ecommerce-app"
                required
              />
            </>
          ) : (
            <label>
              <span className="field-label">Project Folder</span>
              <input
                ref={folderInputRef}
                className="input file-input"
                type="file"
                multiple
                onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
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
            </label>
          )}

          <div className="mt-5 grid gap-4">
            <Select label="Cloud Provider" value={requirements.cloud_provider} values={options.cloud_provider} onChange={(value) => updateRequirement("cloud_provider", value)} />
            <Select label="Migration Goal" value={requirements.migration_goal} values={options.migration_goal} onChange={(value) => updateRequirement("migration_goal", value)} />
            <Select label="Expected Traffic" value={requirements.expected_traffic} values={options.expected_traffic} onChange={(value) => updateRequirement("expected_traffic", value)} />
            <Select label="Budget Preference" value={requirements.budget_preference} values={options.budget_preference} onChange={(value) => updateRequirement("budget_preference", value)} />
            <Select label="Migration Timeline" value={requirements.migration_timeline} values={options.migration_timeline} onChange={(value) => updateRequirement("migration_timeline", value)} />
          </div>

          <button className="mt-6 flex w-full items-center justify-center gap-2 rounded-md bg-moss px-4 py-3 font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-60" disabled={isLoading || (sourceMode === "folder" && selectedFiles.length === 0) || (sourceMode === "github" && !repositoryUrl.trim())}>
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

function Select({ label, value, values, onChange }: { label: string; value: string; values: string[]; onChange: (value: string) => void }) {
  return (
    <label>
      <span className="field-label">{label}</span>
      <select className="input" value={value} onChange={(event) => onChange(event.target.value)}>
        {values.map((item) => (
          <option key={item} value={item}>{item}</option>
        ))}
      </select>
    </label>
  );
}

function Report({ assessment, onDownload }: { assessment: Assessment; onDownload: () => void }) {
  const governance = assessment.governance_assessment ?? {
    risk_level: "Not assessed",
    issues: [],
    passed_checks: [],
    recommendations: [],
    recommendation: "Security and governance assessment was not returned by the API.",
  };

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

        <Panel title="Cost And Strategy">
          <KeyValue label="Provider" value={assessment.recommended_provider} />
          <KeyValue label="Strategy" value={assessment.migration_strategy} />
          <KeyValue label="Monthly" value={`INR ${assessment.cost_estimation.monthly.toLocaleString("en-IN")}`} />
          <KeyValue label="Range" value={assessment.cost_estimation.monthly_range ?? "Not estimated"} />
          <KeyValue label="Annual" value={`INR ${assessment.cost_estimation.annual.toLocaleString("en-IN")}`} />
          <div className="mt-4">
            <List items={assessment.cost_estimation.line_items} />
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

function Panel({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-ink/10 p-4 ${className}`}>
      <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <FileText size={18} className="text-signal" />
        {title}
      </h3>
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
