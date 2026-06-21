import React from "react";
import {
  BarChart3,
  Calendar,
  CalendarDays,
  CheckCircle2,
  CircleDollarSign,
  DollarSign,
  FolderOpen,
  Github,
  GitBranch,
  Gauge,
  Loader2,
  Rocket,
  Scale,
  ServerCog,
  Sparkles,
  Timer,
  Trash2,
  Upload,
  Wrench,
  X,
  Zap,
  RotateCcw,
} from "lucide-react";
import { Report } from "@/components/report/Report";
import { FieldError, RequiredLabel } from "@/components/ui/common";
import cognineLogo from "@/assets/images/cognine_title.png";
import { responseErrorMessage, submitGithubAssessment, submitZipAssessment } from "@/lib/api/assessments";
import { emptyRequirements, fieldLabels, MAX_UPLOAD_BYTES, requiredFieldMessage } from "@/lib/constants";
import type { Assessment, FieldErrors, Requirements, SourceMode } from "@/lib/types";
import { hasRepositoryCloneFailure, needsGithubAccessToken, repositoryCloneFailureMessage } from "@/lib/utils/assessment";
import { downloadAssessmentWordDocument } from "@/lib/utils/wordDocument";

function InfraGuideMark() {
  return (
    <svg className="infra-mark" viewBox="0 0 64 64" role="img" aria-label="InfraGuide AI">
      <defs>
        <linearGradient id="infraGuideMarkBg" x1="8" x2="56" y1="8" y2="56" gradientUnits="userSpaceOnUse">
          <stop stopColor="#1d4ed8" />
          <stop offset="0.56" stopColor="#0f766e" />
          <stop offset="1" stopColor="#f97316" />
        </linearGradient>
        <filter id="infraGuideMarkShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="5" stdDeviation="5" floodColor="#1e3a8a" floodOpacity="0.24" />
        </filter>
      </defs>
      <rect x="5" y="5" width="54" height="54" rx="16" fill="url(#infraGuideMarkBg)" filter="url(#infraGuideMarkShadow)" />
      <path
        d="M18.8 33.4c-3.8 0-6.6-2.5-6.6-5.9 0-3.1 2.3-5.5 5.5-5.9 1.7-4.4 5.7-7.1 10.5-7.1 5.4 0 9.6 3.4 10.8 8.2 4.2.3 7.6 3.5 7.6 7.5 0 4.1-3.5 7.2-7.9 7.2H18.8Z"
        fill="rgba(255,255,255,0.93)"
        stroke="rgba(255,255,255,0.72)"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <circle cx="36" cy="38" r="12" fill="#ffffff" stroke="#172554" strokeWidth="2.4" />
      <circle cx="36" cy="38" r="2.2" fill="#172554" />
      <path d="M41.8 31.2 38.5 41l-8.3 3.8 3.3-9.8 8.3-3.8Z" fill="#f97316" stroke="#172554" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M36 27.8v2.8M36 45.4v2.8M26.9 38H29.7M42.3 38h2.8" stroke="#172554" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function isZipFile(file: File) {
  return file.name.toLowerCase().endsWith(".zip") || ["application/zip", "application/x-zip-compressed"].includes(file.type);
}

function projectNameFromArchive(filename: string) {
  return filename.replace(/\.zip$/i, "").trim() || "Uploaded project";
}

function assessmentErrorMessage(caught: unknown, sourceMode: SourceMode) {
  if (caught instanceof TypeError && sourceMode === "folder") {
    return "Upload failed. Check that the backend is running, then upload a valid project ZIP with source files.";
  }

  if (caught instanceof Error) {
    return caught.message;
  }

  return "Assessment failed";
}

type ChoiceOption = {
  value: string;
  label: string;
  description?: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  tone: "blue" | "teal" | "orange" | "violet" | "red" | "slate" | "green";
};

function AwsLogo() {
  return (
    <span className="provider-brand-logo aws-logo" aria-hidden="true">
      <span>aws</span>
      <i />
    </span>
  );
}

function AzureLogo() {
  return (
    <span className="provider-brand-logo azure-logo" aria-hidden="true">
      <i />
    </span>
  );
}

function GcpLogo() {
  return (
    <span className="provider-brand-logo gcp-logo" aria-hidden="true">
      <i />
    </span>
  );
}

function TrafficSignal({ level = "medium" }: { level?: "low" | "medium" | "high" }) {
  const activeBars = level === "low" ? 1 : level === "medium" ? 3 : 4;

  return (
    <span className={`traffic-signal traffic-signal-${level}`} aria-hidden="true">
      {[1, 2, 3, 4].map((bar) => (
        <i key={bar} className={bar <= activeBars ? "traffic-bar-active" : ""} />
      ))}
    </span>
  );
}

const providerOptions: ChoiceOption[] = [
  { value: "AWS", label: "AWS", icon: AwsLogo, tone: "orange" },
  { value: "Azure", label: "Azure", icon: AzureLogo, tone: "blue" },
  { value: "GCP", label: "GCP", icon: GcpLogo, tone: "green" },
];

const migrationGoalOptions: ChoiceOption[] = [
  { value: "Cost Optimization", label: "Cost Optimize", description: "Reduce and control spend", icon: CircleDollarSign, tone: "green" },
  { value: "Application Modernization", label: "Modernize", description: "Build for cloud native", icon: Rocket, tone: "violet" },
  { value: "Lift-and-Shift", label: "Rehost", description: "Move with minimal change", icon: ServerCog, tone: "blue" },
  { value: "Scalability", label: "Scale", description: "Autoscale and grow", icon: BarChart3, tone: "teal" },
  { value: "Performance Improvement", label: "Refactor", description: "Optimize and improve", icon: Wrench, tone: "slate" },
];

const trafficOptions: ChoiceOption[] = [
  { value: "Low", label: "Low", icon: (props) => <TrafficSignal {...props} level="low" />, tone: "green" },
  { value: "Medium", label: "Medium", icon: (props) => <TrafficSignal {...props} level="medium" />, tone: "orange" },
  { value: "High", label: "High", icon: (props) => <TrafficSignal {...props} level="high" />, tone: "red" },
];

const budgetOptions: ChoiceOption[] = [
  { value: "Low Cost", label: "Cost Optimized", icon: DollarSign, tone: "green" },
  { value: "Balanced", label: "Balanced", icon: Scale, tone: "violet" },
  { value: "Performance Focused", label: "Performance First", icon: Gauge, tone: "red" },
];

const timelineOptions: ChoiceOption[] = [
  { value: "Immediate", label: "Immediate", icon: Zap, tone: "green" },
  { value: "3 Months", label: "3 Months", icon: CalendarDays, tone: "blue" },
  { value: "6 Months", label: "6 Months", icon: Calendar, tone: "slate" },
  { value: "Flexible", label: "Flexible", icon: Timer, tone: "slate" },
];

function ChoiceCard({
  option,
  selected,
  onSelect,
}: {
  option: ChoiceOption;
  selected: boolean;
  onSelect: (value: string) => void;
}) {
  const Icon = option.icon;

  return (
    <button type="button" className={`choice-card choice-card-${option.tone} ${selected ? "choice-card-selected" : ""}`} onClick={() => onSelect(option.value)} aria-pressed={selected}>
      <span className="choice-icon">
        <Icon size={18} />
      </span>
      <span className="choice-copy">
        <span className="choice-label">{option.label}</span>
        {option.description && <span className="choice-description">{option.description}</span>}
      </span>
      {selected && (
        <span className="choice-check" aria-hidden="true">
          <CheckCircle2 size={16} />
        </span>
      )}
    </button>
  );
}

function ChoiceGroup({
  label,
  options,
  value,
  error,
  onChange,
  columns = 3,
}: {
  label: string;
  options: ChoiceOption[];
  value: string;
  error?: string;
  onChange: (value: string) => void;
  columns?: 3 | 4 | 5;
}) {
  return (
    <div className="choice-group">
      <RequiredLabel>{label}</RequiredLabel>
      <div className={`choice-grid choice-grid-${columns} ${error ? "choice-grid-error" : ""}`}>
        {options.map((option) => (
          <ChoiceCard key={option.value} option={option} selected={value === option.value} onSelect={onChange} />
        ))}
      </div>
      {error && <FieldError message={error} />}
    </div>
  );
}

export function App() {
  const [sourceMode, setSourceMode] = React.useState<SourceMode>("github");
  const [repositoryUrl, setRepositoryUrl] = React.useState("");
  const [githubToken, setGithubToken] = React.useState("");
  const [selectedArchive, setSelectedArchive] = React.useState<File | null>(null);
  const [isArchiveProcessing, setIsArchiveProcessing] = React.useState(false);
  const archiveInputRef = React.useRef<HTMLInputElement | null>(null);
  const [githubRequirements, setGithubRequirements] = React.useState<Requirements>(emptyRequirements);
  const [folderRequirements, setFolderRequirements] = React.useState<Requirements>(emptyRequirements);
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});
  const [assessment, setAssessment] = React.useState<Assessment | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isInputModalOpen, setIsInputModalOpen] = React.useState(false);
  const [isTokenModalOpen, setIsTokenModalOpen] = React.useState(false);
  const [toastMessage, setToastMessage] = React.useState("");
  const [isRepositoryLocked, setIsRepositoryLocked] = React.useState(false);
  const requirements = sourceMode === "github" ? githubRequirements : folderRequirements;

  React.useEffect(() => {
    if (!toastMessage) return;

    const timeoutId = window.setTimeout(() => setToastMessage(""), 6000);
    return () => window.clearTimeout(timeoutId);
  }, [toastMessage]);

  React.useEffect(() => {
    if (!isArchiveProcessing) return;

    function clearProcessingAfterCanceledPicker() {
      window.setTimeout(() => {
        if (!archiveInputRef.current?.files?.length) {
          setIsArchiveProcessing(false);
        }
      }, 500);
    }

    window.addEventListener("focus", clearProcessingAfterCanceledPicker);
    return () => window.removeEventListener("focus", clearProcessingAfterCanceledPicker);
  }, [isArchiveProcessing]);

  async function submitAssessment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateMigrationInput();

    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setToastMessage("");
      return;
    }

    if (sourceMode === "github") {
    setIsRepositoryLocked(true);
  }


    setIsLoading(true);
    setToastMessage("");

    try {
      const response = sourceMode === "github" ? await submitGithubAssessment(repositoryUrl, requirements, githubToken) : await submitArchiveAssessment();

      if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
      }

      const nextAssessment = (await response.json()) as Assessment;
      if (sourceMode === "github" && !githubToken.trim() && needsGithubAccessToken(nextAssessment)) {
        setAssessment(null);
        setIsInputModalOpen(false);
        setIsTokenModalOpen(true);
        return;
      }
      if (sourceMode === "github" && !githubToken.trim() && hasRepositoryCloneFailure(nextAssessment)) {
        throw new Error(repositoryCloneFailureMessage(nextAssessment));
      }
      if (sourceMode === "github" && githubToken.trim() && hasRepositoryCloneFailure(nextAssessment)) {
        throw new Error("GitHub clone failed. Check that the repository URL is correct and the access token has read access.");
      }

      setAssessment(nextAssessment);
      setIsInputModalOpen(false);
      if (sourceMode === "github") {
        setIsRepositoryLocked(true);
      }
    } catch (caught) {
      if (sourceMode === "github") {
        setIsRepositoryLocked(false);
      }
      setToastMessage(assessmentErrorMessage(caught, sourceMode));
    } finally {
      setIsLoading(false);
    }
  }

  async function submitPrivateRepositoryToken(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = githubToken.trim();
    if (!token) {
      setToastMessage("Enter a GitHub access token to analyze this private repository.");
      return;
    }

    setIsLoading(true);
    setToastMessage("");

    try {
      const response = await submitGithubAssessment(repositoryUrl, requirements, token);
      if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
      }

      const nextAssessment = (await response.json()) as Assessment;
      if (hasRepositoryCloneFailure(nextAssessment)) {
        throw new Error("GitHub clone failed. Check that the access token has read access to this repository.");
      }

      setAssessment(nextAssessment);
      setIsTokenModalOpen(false);
      setIsInputModalOpen(false);
      setIsRepositoryLocked(true);
    } catch (caught) {
      setToastMessage(caught instanceof Error ? caught.message : "Private repository assessment failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function submitArchiveAssessment() {
    if (!selectedArchive) {
      throw new Error("Select a project ZIP before generating a blueprint.");
    }

    if (!isZipFile(selectedArchive)) {
      throw new Error("Upload a .zip file that contains your project source.");
    }

    if (selectedArchive.size > MAX_UPLOAD_BYTES) {
      throw new Error("Uploaded project ZIP is too large for this MVP scan.");
    }

    const projectName = projectNameFromArchive(selectedArchive.name);
    return submitZipAssessment(selectedArchive, requirements, projectName);
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
    setToastMessage("");
    setAssessment(null);
    setIsArchiveProcessing(false);

    if (mode === "folder") {
      setRepositoryUrl("");
      setGithubToken("");
      setIsRepositoryLocked(false);
      setGithubRequirements(emptyRequirements());
      return;
    }

    setSelectedArchive(null);
    setFolderRequirements(emptyRequirements());
    if (archiveInputRef.current) {
      archiveInputRef.current.value = "";
    }
  }

  function clearSelectedArchive() {
    setSelectedArchive(null);
    setIsArchiveProcessing(false);
    setFieldErrors((current) => ({ ...current, projectFolder: requiredFieldMessage }));
    if (archiveInputRef.current) {
      archiveInputRef.current.value = "";
    }
  }

  function beginArchiveSelection() {
    setIsArchiveProcessing(true);

    if (!archiveInputRef.current) {
      setIsArchiveProcessing(false);
      return;
    }

    archiveInputRef.current.value = "";
    archiveInputRef.current.click();
  }

  function closeMigrationModal() {
  setIsInputModalOpen(false);

  setRepositoryUrl("");
  setGithubToken("");
  setSelectedArchive(null);

  setGithubRequirements(emptyRequirements());
  setFolderRequirements(emptyRequirements());

  setFieldErrors({});
  setToastMessage("");
  setSourceMode("github");
  setIsRepositoryLocked(false);

  if (archiveInputRef.current) {
    archiveInputRef.current.value = "";
  }
}

  function handleArchiveInputChange(event: React.ChangeEvent<HTMLInputElement>) {
    const archive = event.target.files?.[0] ?? null;
    setSelectedArchive(archive);
    setAssessment(null);

    setFieldErrors((current) => ({
      ...current,
      projectFolder: archive ? (isZipFile(archive) ? "" : "Upload a .zip file that contains your project source.") : requiredFieldMessage,
    }));
    window.setTimeout(() => setIsArchiveProcessing(false), 200);
  }

  function clearRepository() {
    setRepositoryUrl("");
    setIsRepositoryLocked(false);
    setAssessment(null);
    setGithubToken("");
    setGithubRequirements(emptyRequirements());
    setToastMessage("");
    setFieldErrors({});
  }

  function startNewAssessment() {
    setAssessment(null);
    setRepositoryUrl("");
    setGithubToken("");
    setSelectedArchive(null);
    setGithubRequirements(emptyRequirements());
    setFolderRequirements(emptyRequirements());
    setFieldErrors({});
    setToastMessage("");
    setSourceMode("github");
    setIsInputModalOpen(false);
    setIsRepositoryLocked(false);
    if (archiveInputRef.current) {
      archiveInputRef.current.value = "";
    }
  }

  function validateMigrationInput() {
    const errors: FieldErrors = {};

    if (sourceMode === "github") {
      const trimmedUrl = repositoryUrl.trim();
      if (!trimmedUrl) {
        errors.repositoryUrl = "GitHub Repository is required";
      } else if (!/^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/.test(trimmedUrl)) {
        errors.repositoryUrl = "Enter a valid GitHub repository URL, for example https://github.com/owner/repository.";
      }
    }

    if (sourceMode === "folder") {
      if (!selectedArchive) {
        errors.projectFolder = "Project ZIP is required";
      } else if (!isZipFile(selectedArchive)) {
        errors.projectFolder = "Upload a .zip file that contains your project source.";
      }
    }

    (Object.keys(requirements) as Array<keyof Requirements>).forEach((key) => {
      if (!requirements[key]) {
        errors[key] = `${fieldLabels[key]} is required`;
      }
    });

    return errors;
  }

  async function downloadBlueprint() {
    if (!assessment) return;
    try {
      await downloadAssessmentWordDocument(assessment);
    } catch (caught) {
      setToastMessage(caught instanceof Error ? caught.message : "Word document download failed.");
    }
  }

  return (
    <main className={`app-shell ${assessment ? "app-shell-report" : "app-shell-input"}`}>
      {assessment && (
      <section className="app-header">
        <div className="app-header-inner">
          <div className="app-brand">
            <InfraGuideMark />
            <div className="app-brand-copy">
              <div className="app-eyebrow">Cloud Migration Intelligence Platform</div>
              <h1 className="app-title">InfraGuide AI</h1>
              <p className="app-subtitle">
                Analyze application repositories, evaluate cloud readiness, map services, estimate costs, and generate a practical migration roadmap.
              </p>
            </div>
          </div>
          {assessment && (
            <button type="button" className="outline-action" onClick={startNewAssessment}>
              <RotateCcw size={18} />
              New assessment
            </button>
          )}
        </div>
      </section>
      )}

      {!assessment ? (
        <section className="landing-page">
          <section className="landing-hero">
            <div className="landing-copy">
              <div className="landing-brand">
                <InfraGuideMark />
                <div>
                  <div className="landing-kicker">AI-powered cloud migration intelligence</div>
                  <h1>InfraGuide AI</h1>
                </div>
              </div>
              <h2>Transform application repositories into <span>cloud-ready</span> architectures.</h2>
              <p>Analyze code, assess cloud readiness, map managed services, estimate regional costs, and generate a practical migration roadmap.</p>
              <button type="button" className="landing-primary-action" onClick={() => setIsInputModalOpen(true)}>
                <Sparkles size={18} />
                Analyze Project
              </button>
            </div>
            <div className="landing-visual" aria-label="Migration assessment preview">
              <div className="visual-cloud" aria-hidden="true">
                <span className="visual-cloud-arrow">↑</span>
              </div>
              <div className="visual-window">
                <div className="visual-sidebar">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <div className="visual-content">
                  <div className="visual-title">Migration Overview</div>
                  <div className="visual-grid">
                    <div className="visual-card visual-score">
                      <span className="score-ring">82%</span>
                      <small>High</small>
                    </div>
                    <div className="visual-card">
                      <small>Estimated Cost</small>
                      <strong>$12,450</strong>
                      <span className="mini-wave" />
                    </div>
                    <div className="visual-card">
                      <small>Migration Effort</small>
                      <strong>Medium</strong>
                      <span className="mini-bars"><i /><i /><i /><i /></span>
                    </div>
                  </div>
                  <div className="visual-lower-grid">
                    <div className="service-map-preview">
                      <div className="visual-section-title">Service Mapping</div>
                      <span className="map-node map-runtime">Runtime</span>
                      <span className="map-node map-database">Database</span>
                      <span className="map-node map-storage">Storage</span>
                      <span className="map-node map-secrets">Secrets</span>
                    </div>
                    <div className="recommendation-preview">
                      <div className="visual-section-title">Recommendations</div>
                      <span><i /> Containerize runtime</span>
                      <span><i /> Move secrets to vault</span>
                      <span><i /> Add monitoring</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="visual-laptop" aria-hidden="true">
                <div className="visual-laptop-screen">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
              <div className="visual-code-badge" aria-hidden="true">{"</>"}</div>
            </div>
          </section>

          <section className="landing-feature-grid" aria-label="InfraGuide capabilities">
            <div className="landing-feature-card"><strong>Repository Analysis</strong><span>Detect languages, frameworks, dependencies, and architecture signals.</span></div>
            <div className="landing-feature-card"><strong>Cloud Readiness</strong><span>Score runtime, database, configuration, and container fit.</span></div>
            <div className="landing-feature-card"><strong>Service Mapping</strong><span>Map application needs to AWS, Azure, and GCP managed services.</span></div>
            <div className="landing-feature-card"><strong>Cost Estimation</strong><span>Compare runtime and service pricing across supported regions.</span></div>
            <div className="landing-feature-card"><strong>Migration Roadmap</strong><span>Generate phased migration steps, validation tasks, and cutover guidance.</span></div>
            <div className="landing-feature-card"><strong>AI Recommendations</strong><span>Get modernization opportunities and governance recommendations.</span></div>
          </section>
          <section className="landing-platforms">
            <span>Supporting major cloud platforms</span>
            <strong className="platform-badge platform-aws"><span>aws</span></strong>
            <strong className="platform-badge platform-azure"><span className="azure-mark" /> Microsoft Azure</strong>
            <strong className="platform-badge platform-google"><span className="google-cloud-mark" /> Google Cloud</strong>
          </section>
        </section>
      ) : (
        <section className="app-content app-content-report">
          <section className="report-panel app-card">
            <Report assessment={assessment} onDownload={downloadBlueprint} />
          </section>
        </section>
      )}

      <footer className="app-footer">
        <span>InfraGuide AI</span>
        <span className="footer-brand">
          Powered by
          <img className="footer-logo" src={cognineLogo} alt="Cognine" />
        </span>
      </footer>

      {toastMessage && (
        <div className="toast-message" role="alert" aria-live="assertive">
          <span>{toastMessage}</span>
          <button type="button" className="toast-close" onClick={() => setToastMessage("")} aria-label="Dismiss notification">
            <X size={16} />
          </button>
        </div>
      )}

      {isInputModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-panel migration-input-modal" role="dialog" aria-modal="true" aria-labelledby="migrationInputTitle">
            <div className="modal-header">
              <div>
                <h2 id="migrationInputTitle" className="modal-title">Migration Input</h2>
                <p className="modal-copy">Select a source and migration profile to generate your blueprint.</p>
              </div>
              <button type="button" className="clear-folder-button" onClick={closeMigrationModal} aria-label="Close migration input">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={submitAssessment} className="modal-migration-form">
              <div className="source-tabs">
                <button type="button" className={`source-tab ${sourceMode === "github" ? "source-tab-active" : ""}`} onClick={() => switchSourceMode("github")}>
                  <Github size={17} />
                  GitHub URL
                </button>
                <button type="button" className={`source-tab ${sourceMode === "folder" ? "source-tab-active" : ""}`} onClick={() => switchSourceMode("folder")}>
                  <Upload size={17} />
                  Upload ZIP
                </button>
              </div>

              {sourceMode === "github" ? (
                <>
                  <RequiredLabel htmlFor="repositoryUrl">GitHub Repository</RequiredLabel>
                  <div className="repo-input-row">
                    <input
                      id="repositoryUrl"
                      className={`input repo-input ${isRepositoryLocked ? "input-locked" : ""} ${fieldErrors.repositoryUrl ? "input-error" : ""}`}
                      value={repositoryUrl}
                      readOnly={isRepositoryLocked || isLoading}
                      title={repositoryUrl}
                      onChange={(event) => {
                        if (isRepositoryLocked) return;
                        const nextUrl = event.target.value;
                        setRepositoryUrl(nextUrl);
                        setFieldErrors((current) => ({
                          ...current,
                          repositoryUrl: nextUrl.trim() ? "" : "GitHub Repository is required",
                        }));
                      }}
                      placeholder="https://github.com/company/ecommerce-app"
                    />

                    {repositoryUrl.trim() && !isRepositoryLocked && (
                      <button type="button" className="repo-clear-button" onClick={clearRepository} title="Clear Repository">
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                  {fieldErrors.repositoryUrl && <FieldError message={fieldErrors.repositoryUrl} />}
                </>
              ) : (
                <label>
                  <RequiredLabel>Project ZIP</RequiredLabel>
                  <div className={`folder-picker-box ${fieldErrors.projectFolder ? "input-error" : ""}`}>
                    <button type="button" className="folder-picker-button" onClick={beginArchiveSelection} disabled={isArchiveProcessing}>
                      {isArchiveProcessing ? <Loader2 className="animate-spin" size={16} /> : <FolderOpen size={16} />}
                      <span className="folder-picker-text">
                        {isArchiveProcessing ? "Preparing ZIP..." : selectedArchive?.name ?? "Choose project ZIP"}
                      </span>
                    </button>
                    {selectedArchive && (
                      <button type="button" className="clear-folder-button" onClick={clearSelectedArchive} aria-label="Remove selected ZIP">
                        <X size={16} />
                      </button>
                    )}
                  </div>
                  <input
                    ref={archiveInputRef}
                    className="hidden-file-input"
                    type="file"
                    accept=".zip,application/zip,application/x-zip-compressed"
                    onChange={handleArchiveInputChange}
                  />
                  {!selectedArchive && <span className="field-help">Upload a .zip archive of your project source.</span>}
                  {fieldErrors.projectFolder && <FieldError message={fieldErrors.projectFolder} />}
                </label>
              )}

              <div className="profile-builder">
                <div className="profile-row profile-top-row">
                  <ChoiceGroup label="Cloud Provider" options={providerOptions} value={requirements.cloud_provider} error={fieldErrors.cloud_provider} onChange={(value) => updateRequirement("cloud_provider", value)} columns={3} />
                  <ChoiceGroup label="Migration Timeline" options={timelineOptions} value={requirements.migration_timeline} error={fieldErrors.migration_timeline} onChange={(value) => updateRequirement("migration_timeline", value)} columns={4} />
                </div>
                <ChoiceGroup label="Migration Goal" options={migrationGoalOptions} value={requirements.migration_goal} error={fieldErrors.migration_goal} onChange={(value) => updateRequirement("migration_goal", value)} columns={5} />
                <div className="profile-row">
                  <ChoiceGroup label="Expected Traffic" options={trafficOptions} value={requirements.expected_traffic} error={fieldErrors.expected_traffic} onChange={(value) => updateRequirement("expected_traffic", value)} columns={3} />
                  <ChoiceGroup label="Budget Preference" options={budgetOptions} value={requirements.budget_preference} error={fieldErrors.budget_preference} onChange={(value) => updateRequirement("budget_preference", value)} columns={3} />
                </div>
              </div>

              <div className="migration-modal-footer">
                <button type="button" className="secondary-action modal-cancel-action" onClick={closeMigrationModal}>
                  Cancel
                </button>
                <button className="primary-action modal-generate-action" disabled={isLoading}>
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : <ServerCog size={18} />}
                  Generate Blueprint
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {isTokenModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="privateRepoTitle">
            <div className="modal-header">
              <div>
                <h2 id="privateRepoTitle" className="modal-title">Private GitHub Repository</h2>
                <p className="modal-copy">This GitHub URL is private or cannot be accessed publicly. Please provide an access token to continue.</p>
              </div>
              <button type="button" className="clear-folder-button" onClick={() => setIsTokenModalOpen(false)} aria-label="Close access token dialog">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={submitPrivateRepositoryToken}>
              <label htmlFor="modalGithubToken">
                <span className="field-label">Access Token</span>
                <input id="modalGithubToken" className="input" value={githubToken} onChange={(event) => setGithubToken(event.target.value)} placeholder="Paste GitHub access token" type="password" autoComplete="off" />
              </label>

              <div className="token-help">
                <p className="token-help-title">Steps to get an access token:</p>
                <ol className="token-help-list">
                  <li>Open GitHub Settings, then Developer settings.</li>
                  <li>Go to Personal access tokens and create a fine-grained token.</li>
                  <li>Select the private repository you want to analyze.</li>
                  <li>Give read-only access to repository contents and metadata.</li>
                  <li>Generate the token, copy it, and paste it here.</li>
                </ol>
              </div>

              <div className="modal-actions">
                <button type="button" className="secondary-action" onClick={() => setIsTokenModalOpen(false)}>
                  Cancel
                </button>
                <button className="modal-primary-action" disabled={isLoading || !githubToken.trim()}>
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
