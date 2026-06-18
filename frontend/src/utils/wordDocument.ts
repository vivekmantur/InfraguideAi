import type { Assessment } from "../types";
import { formatMoney, list } from "./format";

export function downloadAssessmentWordDocument(assessment: Assessment) {
  const html = renderAssessmentWordHtml(assessment);
  const blob = new Blob(["\ufeff", html], { type: "application/msword;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "infraguide-ai-migration-blueprint.doc";
  anchor.click();
  URL.revokeObjectURL(url);
}

function renderAssessmentWordHtml(assessment: Assessment) {
  const stack = assessment.technology_stack;
  const cost = assessment.cost_estimation;
  const governance = assessment.governance_assessment ?? {
    risk_level: "Not assessed",
    issues: [],
    passed_checks: [],
    recommendations: [],
    recommendation: "Security and governance assessment was not returned by the API.",
  };

  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>InfraGuide AI Migration Blueprint</title>
  <style>
    @page { margin: 0.7in; }
    body {
      font-family: Calibri, Arial, sans-serif;
      color: #17201b;
      font-size: 11pt;
      line-height: 1.35;
    }
    h1 {
      color: #2f5d50;
      font-size: 24pt;
      margin: 0 0 8pt;
    }
    h2 {
      color: #2f5d50;
      font-size: 16pt;
      margin: 18pt 0 8pt;
      border-bottom: 1pt solid #cfd8d3;
      padding-bottom: 4pt;
    }
    h3 {
      color: #17201b;
      font-size: 13pt;
      margin: 12pt 0 6pt;
    }
    p {
      margin: 0 0 8pt;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 6pt 0 12pt;
    }
    th {
      background: #eef2ef;
      color: #17201b;
      font-weight: bold;
      text-align: left;
    }
    th, td {
      border: 1pt solid #cfd8d3;
      padding: 6pt;
      vertical-align: top;
    }
    ul, ol {
      margin-top: 4pt;
      margin-bottom: 10pt;
    }
    li {
      margin-bottom: 4pt;
    }
    .meta {
      color: #4f5f57;
      margin-bottom: 16pt;
    }
    .summary-box {
      border: 1pt solid #cfd8d3;
      background: #f7faf8;
      padding: 10pt;
      margin: 10pt 0 14pt;
    }
    .score {
      font-size: 18pt;
      font-weight: bold;
      color: #d9663d;
    }
  </style>
</head>
<body>
  <h1>InfraGuide AI Migration Blueprint</h1>
  <p class="meta">Generated migration assessment and cloud modernization plan.</p>

  <div class="summary-box">
    <p><strong>Architecture Summary:</strong> ${escapeHtml(assessment.architecture_summary)}</p>
    <p><strong>Recommended Provider:</strong> ${escapeHtml(assessment.recommended_provider)}</p>
    <p><strong>Migration Strategy:</strong> ${escapeHtml(assessment.migration_strategy)}</p>
    <p><strong>Readiness Score:</strong> <span class="score">${assessment.cloud_readiness.score}%</span></p>
  </div>

  <h2>1. Technology Stack</h2>
  ${keyValueTable([
    ["Project Summary", stack.project_summary ?? assessment.architecture_summary],
    ["Languages", list(stack.languages)],
    ["Frameworks", list(stack.frameworks)],
    ["Runtime", list(stack.runtimes)],
    ["Hosting Model", stack.hosting_model ?? "Not detected"],
    ["Deployment Model", stack.deployment_model ?? "Not detected"],
    ["Triggers", list(stack.triggers)],
    ["Databases", list(stack.databases)],
    ["Package Managers", list(stack.package_managers)],
    ["Container Configurations", list(stack.container_configs)],
    ["Cloud Dependencies", list(stack.cloud_dependencies)],
  ])}

  <h2>2. Cloud Readiness</h2>
  ${keyValueTable([
    ["Score", `${assessment.cloud_readiness.score}%`],
    ["Complexity", assessment.cloud_readiness.complexity],
    ["Runtime Compatibility", assessment.cloud_readiness.runtime_compatibility],
    ["Database Compatibility", assessment.cloud_readiness.database_compatibility],
    ["Container Readiness", assessment.cloud_readiness.container_readiness],
    ["Configuration Readiness", assessment.cloud_readiness.configuration_readiness],
  ])}
  <h3>Score Breakdown</h3>
  ${listHtml(assessment.cloud_readiness.score_breakdown)}

  <h2>3. Recommended Cloud Services</h2>
  <table>
    <thead>
      <tr><th>Component</th><th>Current State</th><th>Recommended Service</th></tr>
    </thead>
    <tbody>
      ${assessment.recommended_services.map((service) => `<tr><td>${escapeHtml(service.component)}</td><td>${escapeHtml(service.current)}</td><td>${escapeHtml(service.recommended)}</td></tr>`).join("")}
    </tbody>
  </table>

  <h2>4. Cost Estimate</h2>
  ${keyValueTable([
    ["Currency", cost.currency],
    ["Monthly Cost", formatMoney(cost.currency, cost.monthly)],
    ["Monthly Range", cost.monthly_range ?? "Not estimated"],
    ["Annual Cost", formatMoney(cost.currency, cost.annual)],
  ])}
  <h3>Line Items</h3>
  ${listHtml(cost.line_items)}
  <h3>Assumptions</h3>
  ${listHtml(cost.assumptions)}

  <h2>5. Dependencies</h2>
  ${listHtml(stack.dependency_graph)}

  <h2>6. Security And Governance</h2>
  ${keyValueTable([
    ["Risk Level", governance.risk_level],
    ["Recommendation", governance.recommendation],
  ])}
  <h3>Passed Checks</h3>
  ${listHtml(governance.passed_checks)}
  <h3>Issues</h3>
  ${listHtml(governance.issues)}
  <h3>Recommendations</h3>
  ${listHtml(governance.recommendations)}

  <h2>7. Modernization Opportunities</h2>
  ${listHtml(assessment.modernization_opportunities)}

  <h2>8. Migration Roadmap</h2>
  ${listHtml(assessment.migration_roadmap, true)}

  ${assessment.warnings.length > 0 ? `<h2>9. Warnings</h2>${listHtml(assessment.warnings)}` : ""}
</body>
</html>`;
}

function keyValueTable(rows: Array<[string, string]>) {
  return `<table><tbody>${rows.map(([label, value]) => `<tr><th style="width: 32%;">${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`).join("")}</tbody></table>`;
}

function listHtml(items: string[] | undefined, numbered = false) {
  if (!items?.length) {
    return "<p>None</p>";
  }

  const tag = numbered ? "ol" : "ul";
  return `<${tag}>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</${tag}>`;
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
