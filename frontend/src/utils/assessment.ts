import type { Assessment } from "../types";

export function hasRepositoryCloneFailure(assessment: Assessment) {
  return assessment.warnings?.some((warning) => warning.toLowerCase().startsWith("repository clone failed:")) ?? false;
}

export function needsGithubAccessToken(assessment: Assessment) {
  return assessment.warnings?.some((warning) => {
    const normalizedWarning = warning.toLowerCase();
    return normalizedWarning.startsWith("repository clone failed:") && normalizedWarning.includes("without a github access token");
  }) ?? false;
}

export function repositoryCloneFailureMessage(assessment: Assessment) {
  const cloneWarning = assessment.warnings?.find((warning) => warning.toLowerCase().startsWith("repository clone failed:"));
  return cloneWarning ?? "GitHub clone failed. Check that the repository URL is correct and try again.";
}
