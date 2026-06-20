import type { Requirements } from "./types";

const defaultApiBaseUrl = `${window.location.protocol}//${window.location.hostname}:9000`;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl;
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

export const IGNORED_UPLOAD_PARTS = new Set([
  ".git",
  "node_modules",
  "vendor",
  "bin",
  "obj",
  "dist",
  "build",
  ".venv",
  "venv",
  "env",
  "__pycache__",
]);

export const options = {
  cloud_provider: ["AWS", "Azure", "GCP"],
  migration_goal: ["Application Modernization", "Cost Optimization", "Lift-and-Shift", "Scalability", "Performance Improvement"],
  expected_traffic: ["Low", "Medium", "High"],
  budget_preference: ["Balanced", "Low Cost", "Performance Focused"],
  migration_timeline: ["3 Months", "Immediate", "6 Months", "Flexible"],
};

export const fieldLabels = {
  repositoryUrl: "GitHub Repository",
  projectFolder: "Project ZIP",
  cloud_provider: "Cloud Provider",
  migration_goal: "Migration Goal",
  expected_traffic: "Expected Traffic",
  budget_preference: "Budget Preference",
  migration_timeline: "Migration Timeline",
};

export const requiredFieldMessage = "This field is required";

export const emptyRequirements = (): Requirements => ({
  cloud_provider: "",
  migration_goal: "",
  expected_traffic: "",
  budget_preference: "",
  migration_timeline: "",
});

export const pricingRegions: Record<string, string[]> = {
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
