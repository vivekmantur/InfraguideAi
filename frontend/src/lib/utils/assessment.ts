import type { Assessment } from "@/lib/types";

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
  return friendlyRepositoryCloneFailureMessage(cloneWarning);
}

function friendlyRepositoryCloneFailureMessage(warning?: string) {
  const normalizedWarning = (warning ?? "").toLowerCase();

  if (normalizedWarning.includes("filename too long") || normalizedWarning.includes("unable to checkout working tree")) {
    return "GitHub clone failed because this repository contains file paths that are too long for Windows checkout. Try enabling long paths in Windows/Git, or upload a project ZIP without build output folders like bin and obj.";
  }

  if (normalizedWarning.includes("without a github access token") || normalizedWarning.includes("authentication") || normalizedWarning.includes("not accessible")) {
    return "GitHub clone failed because the repository is private or not accessible. Provide a GitHub access token with read access and try again.";
  }

  if (normalizedWarning.includes("repository not found")) {
    return "GitHub clone failed because the repository was not found. Check the owner, repository name, and access permissions.";
  }

  if (normalizedWarning.includes("timed out") || normalizedWarning.includes("timeout")) {
    return "GitHub clone timed out. Try again, or upload a project ZIP directly.";
  }

  return "GitHub clone failed. Check that the repository URL is correct and try again.";
}
