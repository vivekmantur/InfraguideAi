import { API_BASE_URL } from "../constants";
import type { Requirements } from "../types";

export function submitGithubAssessment(repositoryUrl: string, requirements: Requirements, githubToken = "") {
  const trimmedUrl = repositoryUrl.trim();

  return fetch(`${API_BASE_URL}/assessments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_url: trimmedUrl,
      github_token: githubToken.trim() || undefined,
      requirements,
    }),
  });
}

export function submitUploadedAssessment(files: File[], requirements: Requirements, projectName: string) {
  const formData = new FormData();
  formData.append("requirements", JSON.stringify(requirements));
  formData.append("project_name", projectName);
  for (const file of files) {
    formData.append("files", file, file.webkitRelativePath || file.name);
  }

  return fetch(`${API_BASE_URL}/assessments/upload`, {
    method: "POST",
    body: formData,
  });
}

export function submitZipAssessment(archive: File, requirements: Requirements, projectName: string) {
  const formData = new FormData();
  formData.append("requirements", JSON.stringify(requirements));
  formData.append("project_name", projectName);
  formData.append("archive", archive, archive.name);

  return fetch(`${API_BASE_URL}/assessments/upload-zip`, {
    method: "POST",
    body: formData,
  });
}

export async function responseErrorMessage(response: Response) {
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
