import React from "react";
import { CloudCog, FolderOpen, GitBranch, Loader2, Route, ServerCog, Trash2, X } from "lucide-react";
import { responseErrorMessage, submitGithubAssessment, submitUploadedAssessment } from "./api/assessments";
import { FieldError, Metric, RequiredLabel, Select } from "./components/common";
import { Report } from "./components/Report";
import { emptyRequirements, fieldLabels, MAX_UPLOAD_BYTES, options, requiredFieldMessage } from "./constants";
import type { Assessment, FieldErrors, Requirements, SourceMode } from "./types";
import { hasRepositoryCloneFailure, needsGithubAccessToken, repositoryCloneFailureMessage } from "./utils/assessment";
import { analyzableFiles } from "./utils/files";
import { downloadAssessmentWordDocument } from "./utils/wordDocument";

export function App() {
  const [sourceMode, setSourceMode] = React.useState<SourceMode>("github");
  const [repositoryUrl, setRepositoryUrl] = React.useState("");
  const [githubToken, setGithubToken] = React.useState("");
  const [selectedFiles, setSelectedFiles] = React.useState<File[]>([]);
  const folderInputRef = React.useRef<HTMLInputElement | null>(null);
  const [githubRequirements, setGithubRequirements] = React.useState<Requirements>(emptyRequirements);
  const [folderRequirements, setFolderRequirements] = React.useState<Requirements>(emptyRequirements);
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});
  const [assessment, setAssessment] = React.useState<Assessment | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isTokenModalOpen, setIsTokenModalOpen] = React.useState(false);
  const [error, setError] = React.useState("");
  const [isRepositoryLocked, setIsRepositoryLocked] = React.useState(false);
  const requirements = sourceMode === "github" ? githubRequirements : folderRequirements;
  const uploadableFiles = React.useMemo(() => analyzableFiles(selectedFiles), [selectedFiles]);

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
      const response = sourceMode === "github" ? await submitGithubAssessment(repositoryUrl, requirements, githubToken) : await submitFolderAssessment();

      if (!response.ok) {
        throw new Error(await responseErrorMessage(response));
      }

      const nextAssessment = (await response.json()) as Assessment;
      if (sourceMode === "github" && !githubToken.trim() && needsGithubAccessToken(nextAssessment)) {
        setAssessment(null);
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
      if (sourceMode === "github") {
        setIsRepositoryLocked(true);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Assessment failed");
    } finally {
      setIsLoading(false);
    }
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
      setIsRepositoryLocked(true);
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

    const projectName = uploadFiles[0].webkitRelativePath?.split("/")[0] || "Uploaded folder";
    return submitUploadedAssessment(uploadFiles, requirements, projectName);
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

  function clearRepository() {
    setRepositoryUrl("");
    setIsRepositoryLocked(false);
    setAssessment(null);
    setGithubToken("");
    setGithubRequirements(emptyRequirements());
    setError("");
    setFieldErrors({});
  }

  function validateMigrationInput() {
    const errors: FieldErrors = {};

    if (sourceMode === "github" && !repositoryUrl.trim()) {
      errors.repositoryUrl = "GitHub Repository is required";
    }

    if (sourceMode === "folder" && selectedFiles.length === 0) {
      errors.projectFolder = "Project Folder is required";
    }

    (Object.keys(requirements) as Array<keyof Requirements>).forEach((key) => {
      if (!requirements[key]) {
        errors[key] = `${fieldLabels[key]} is required`;
      }
    });

    return errors;
  }

  function downloadBlueprint() {
    if (!assessment) return;
    downloadAssessmentWordDocument(assessment);
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

      <section className="grid w-full items-start gap-5 px-5 py-5 lg:grid-cols-[420px_minmax(0,1fr)]">
        <form onSubmit={submitAssessment} className="main-panel rounded-lg border border-ink/10 bg-white p-5 shadow-panel lg:sticky lg:top-5">
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
              <div className="flex items-center gap-2">
                <input
                  id="repositoryUrl"
                  className={`input flex-1 ${isRepositoryLocked ? "bg-gray-100 cursor-not-allowed" : ""} ${fieldErrors.repositoryUrl ? "input-error" : ""}`}
                  value={repositoryUrl}
                  readOnly={isRepositoryLocked}
                  title={repositoryUrl}
                  onChange={(event) => {
                    if (isRepositoryLocked) return;
                    setRepositoryUrl(event.target.value);
                    setFieldErrors((current) => ({ ...current, repositoryUrl: event.target.value.trim() ? "" : "GitHub Repository is required" }));
                  }}
                  placeholder="https://github.com/company/ecommerce-app"
                />

                {repositoryUrl.trim() && (
                  <button type="button" className="h-[42px] w-[42px] shrink-0 flex items-center justify-center rounded-md border border-gray-300 text-gray-500 hover:bg-red-50 hover:border-red-500 hover:text-red-600 transition-colors" onClick={clearRepository} title="Clear Repository">
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
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

        <section className="main-panel rounded-lg border border-ink/10 bg-white p-5 shadow-panel">
          {assessment ? (
            <Report assessment={assessment} onDownload={downloadBlueprint} />
          ) : (
            <div className="flex h-full min-h-[520px] flex-col items-center justify-center text-center">
              <Route size={44} className="mb-4 text-signal" />
              <h2 className="text-2xl font-semibold">Migration blueprint output</h2>
              <p className="mt-3 max-w-xl text-ink/65">Submit a repository and migration profile to generate stack analysis, readiness scoring, service mapping, strategy, cost estimate, and roadmap.</p>
            </div>
          )}
        </section>
      </section>

      {isTokenModalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="privateRepoTitle">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 id="privateRepoTitle" className="text-xl font-semibold">Private GitHub Repository</h2>
                <p className="mt-2 text-sm leading-6 text-ink/70">This GitHub URL is private or cannot be accessed publicly. Please provide an access token to continue.</p>
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
