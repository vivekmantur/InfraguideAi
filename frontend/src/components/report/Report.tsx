import React from "react";
import { ArrowDownToLine } from "lucide-react";
import { fetchRuntimeSupport, fetchServiceAvailability, parseRuntimeSupport, parseServiceAvailability } from "@/lib/api/cloudIntelligence";
import type { Assessment, RegionalPrice, RuntimeSupportResult, ServiceAvailabilityResult } from "@/lib/types";
import { formatMoney, list } from "@/lib/utils/format";
import { RegionalPricingModal } from "@/components/report/RegionalPricingModal";
import { KeyValue, List, Panel } from "@/components/ui/common";

export function Report({ assessment, onDownload }: { assessment: Assessment; onDownload: () => void }) {
  const [activeTab, setActiveTab] = React.useState<"overview" | "cloud" | "plan">("overview");
  const [isPricingModalOpen, setIsPricingModalOpen] = React.useState(false);
  const [appliedRegionalPrice, setAppliedRegionalPrice] = React.useState<RegionalPrice | null>(null);
  const [serviceAvailability, setServiceAvailability] = React.useState<ServiceAvailabilityResult | null>(null);
  const [runtimeSupport, setRuntimeSupport] = React.useState<RuntimeSupportResult | null>(null);
  const [cloudIntelligenceError, setCloudIntelligenceError] = React.useState("");
  const governance = assessment.governance_assessment ?? {
    risk_level: "Not assessed",
    issues: [],
    passed_checks: [],
    recommendations: [],
    recommendation: "Security and governance assessment was not returned by the API.",
  };
  const activeMonthlyValue = appliedRegionalPrice ? formatMoney(appliedRegionalPrice.currency, appliedRegionalPrice.total_monthly) : formatMoney(assessment.cost_estimation.currency, assessment.cost_estimation.monthly);
  const activeAnnualValue = appliedRegionalPrice ? formatMoney(appliedRegionalPrice.currency, appliedRegionalPrice.total_monthly * 12) : formatMoney(assessment.cost_estimation.currency, assessment.cost_estimation.annual);
  const activeRangeValue = appliedRegionalPrice ? `${appliedRegionalPrice.region} selected` : assessment.cost_estimation.monthly_range ?? "Not estimated";
  const activeRegion = appliedRegionalPrice?.region ?? defaultCostRegion(assessment);
  const targetRuntimeService = applicationRuntimeService(assessment);
  const activeLineItems = appliedRegionalPrice
    ? [
        `${appliedRegionalPrice.runtime_sku || "Runtime"} in ${appliedRegionalPrice.region}: ${formatMoney(appliedRegionalPrice.currency, appliedRegionalPrice.runtime_monthly)}/month`,
        ...((appliedRegionalPrice.service_breakdown ?? []).map((service) => `${service.component}: ${service.recommended ?? "Managed service"}: ${formatMoney(service.currency ?? appliedRegionalPrice.currency, service.monthly_cost)}/month`)),
      ]
    : assessment.cost_estimation.line_items;
  const activeAssumptions = appliedRegionalPrice
    ? [
        `Selected regional estimate: ${appliedRegionalPrice.region}.`,
        "Applied region values are shown directly from the regional pricing comparison.",
      ]
    : assessment.cost_estimation.assumptions ?? [];

  React.useEffect(() => {
    let isActive = true;

    async function loadCloudIntelligence() {
      setCloudIntelligenceError("");

      try {
        const [availabilityResponse, runtimeResponse] = await Promise.all([
          fetchServiceAvailability({
            provider: assessment.recommended_provider,
            region: activeRegion,
            services: assessment.recommended_services,
          }),
          fetchRuntimeSupport({
            provider: assessment.recommended_provider,
            targetService: targetRuntimeService,
            runtimes: assessment.technology_stack.runtimes ?? [],
            frameworks: assessment.technology_stack.frameworks ?? [],
          }),
        ]);

        const [availability, runtime] = await Promise.all([
          parseServiceAvailability(availabilityResponse),
          parseRuntimeSupport(runtimeResponse),
        ]);

        if (isActive) {
          setServiceAvailability(availability);
          setRuntimeSupport(runtime);
        }
      } catch (caught) {
        if (isActive) {
          setServiceAvailability(null);
          setRuntimeSupport(null);
          setCloudIntelligenceError(caught instanceof Error ? caught.message : "Cloud intelligence lookup failed");
        }
      }
    }

    loadCloudIntelligence();

    return () => {
      isActive = false;
    };
  }, [assessment, activeRegion, targetRuntimeService]);

  return (
    <div>
      <div className="report-header">
        <div>
          <h2 className="report-title">Migration Blueprint</h2>
          <p className="report-summary">{assessment.architecture_summary}</p>
        </div>
        <button onClick={onDownload} className="outline-action">
          <ArrowDownToLine size={18} />
          Download
        </button>
      </div>

      <div className="report-tabs" role="tablist" aria-label="Report sections">
        <button type="button" className={`report-tab ${activeTab === "overview" ? "report-tab-active" : ""}`} onClick={() => setActiveTab("overview")}>Overview</button>
        <button type="button" className={`report-tab ${activeTab === "cloud" ? "report-tab-active" : ""}`} onClick={() => setActiveTab("cloud")}>Cloud Fit</button>
        <button type="button" className={`report-tab ${activeTab === "plan" ? "report-tab-active" : ""}`} onClick={() => setActiveTab("plan")}>Migration Plan</button>
      </div>

      <div className="report-tab-content">
      {activeTab === "overview" && (
        <div className="report-overview-stack">
          <div className="overview-metrics">
            <div className="overview-metric-card">
              <span>Readiness</span>
              <strong>{assessment.cloud_readiness.score}%</strong>
            </div>
            <div className="overview-metric-card">
              <span>Provider</span>
              <strong>{assessment.recommended_provider}</strong>
            </div>
            <div className="overview-metric-card">
              <span>Strategy</span>
              <strong>{assessment.migration_strategy}</strong>
            </div>
          </div>
          <div className="report-card-grid report-card-grid-summary">
          <Panel title="Assessment Summary">
            <p className="summary-narrative">{overviewSummary(assessment, governance.risk_level)}</p>
          </Panel>
          <Panel title="Application Snapshot">
            <KeyValue label="Languages" value={list(assessment.technology_stack.languages)} />
            <KeyValue label="Frameworks" value={list(assessment.technology_stack.frameworks)} />
            <KeyValue label="Runtime" value={list(assessment.technology_stack.runtimes)} />
            <KeyValue label="Database" value={list(assessment.technology_stack.databases)} />
          </Panel>
          <Panel title="Migration Direction">
            <p className="summary-narrative">{migrationDirectionSummary(assessment, activeRegion, activeMonthlyValue)}</p>
          </Panel>
          </div>
        </div>
      )}

      {activeTab === "cloud" && (
        <div className="report-card-grid">
          <TechnologyStackPanel assessment={assessment} />
          <CloudReadinessPanel assessment={assessment} />
          <RecommendedServicesPanel assessment={assessment} />
          <CloudValidationPanel serviceAvailability={serviceAvailability} cloudIntelligenceError={cloudIntelligenceError} />
          <RuntimeCompatibilityPanel runtimeSupport={runtimeSupport} cloudIntelligenceError={cloudIntelligenceError} />
          <CostStrategyPanel
            assessment={assessment}
            activeRegion={activeRegion}
            activeMonthlyValue={activeMonthlyValue}
            activeRangeValue={activeRangeValue}
            activeAnnualValue={activeAnnualValue}
            activeLineItems={activeLineItems}
            activeAssumptions={activeAssumptions}
            onCompare={() => setIsPricingModalOpen(true)}
          />
          <Panel title="Dependencies">
            <KeyValue label="Cloud" value={list(assessment.technology_stack.cloud_dependencies)} />
            <List items={assessment.technology_stack.dependency_graph} />
          </Panel>
          <Panel title="Security">
            <KeyValue label="Risk" value={governance.risk_level} />
            <List items={[...(governance.passed_checks ?? []), ...(governance.issues ?? []), ...(governance.recommendations ?? [])]} />
          </Panel>
        </div>
      )}

      {activeTab === "plan" && (
        <div className="report-card-grid report-card-grid-wide">
          <Panel title="Modernization">
            <List items={assessment.modernization_opportunities} />
          </Panel>
          <Panel title="Roadmap">
            <List items={assessment.migration_roadmap} numbered />
          </Panel>
        </div>
      )}

      {assessment.warnings.length > 0 && <div className="warning-box">{assessment.warnings.join(" ")}</div>}
      </div>

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

function TechnologyStackPanel({ assessment }: { assessment: Assessment }) {
  return (
    <Panel title="Technology Stack">
      <KeyValue label="Languages" value={list(assessment.technology_stack.languages)} />
      <KeyValue label="Frameworks" value={list(assessment.technology_stack.frameworks)} />
      <KeyValue label="Runtime" value={list(assessment.technology_stack.runtimes)} />
      <KeyValue label="Hosting" value={assessment.technology_stack.hosting_model ?? "Not detected"} />
      <KeyValue label="Deployment" value={assessment.technology_stack.deployment_model ?? "Not detected"} />
      <KeyValue label="Triggers" value={list(assessment.technology_stack.triggers)} />
      <KeyValue label="Databases" value={list(assessment.technology_stack.databases)} />
      <KeyValue label="Containers" value={list(assessment.technology_stack.container_configs)} />
    </Panel>
  );
}

function CloudReadinessPanel({ assessment }: { assessment: Assessment }) {
  return (
    <Panel title="Cloud Readiness">
      <div className="readiness-track">
        <div className="readiness-bar" style={{ width: `${assessment.cloud_readiness.score}%` }} />
      </div>
      <KeyValue label="Score" value={`${assessment.cloud_readiness.score}%`} />
      <KeyValue label="Complexity" value={assessment.cloud_readiness.complexity} />
      <KeyValue label="Container" value={assessment.cloud_readiness.container_readiness} />
      <KeyValue label="Configuration" value={assessment.cloud_readiness.configuration_readiness} />
      <div className="section-spacer">
        <List items={assessment.cloud_readiness.score_breakdown} />
      </div>
    </Panel>
  );
}

function RecommendedServicesPanel({ assessment }: { assessment: Assessment }) {
  return (
    <Panel title="Recommended Services">
      <div className="service-list">
        {assessment.recommended_services.map((item) => (
          <div key={item.component} className="service-item">
            <div className="service-title">{item.component}</div>
            <div className="service-path">{item.current} {"->"} {item.recommended}</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function CloudValidationPanel({
  serviceAvailability,
  cloudIntelligenceError,
}: {
  serviceAvailability: ServiceAvailabilityResult | null;
  cloudIntelligenceError: string;
}) {
  return (
    <Panel title="Cloud Service Validation">
      {serviceAvailability ? (
        <>
          <KeyValue label="Region" value={serviceAvailability.region} />
          <KeyValue label="Catalog" value={`${serviceAvailability.catalog_source ?? "catalog"} ${serviceAvailability.catalog_version ?? ""}`.trim()} />
          <KeyValue label="Region Support" value={serviceAvailability.region_supported ? "Supported" : "Not supported"} />
          <div className="section-spacer">
            <div className="subsection-label">Available Services</div>
            <List items={serviceAvailability.available.map((item) => `${item.component ?? item.category}: ${item.service}`)} />
          </div>
          {serviceAvailability.unavailable.length > 0 && (
            <div className="section-spacer">
              <div className="subsection-label">Needs Review</div>
              <List items={serviceAvailability.unavailable.map((item) => `${item.component ?? item.category}: ${item.service}`)} />
            </div>
          )}
          {serviceAvailability.notes.length > 0 && (
            <div className="section-spacer">
              <List items={serviceAvailability.notes} />
            </div>
          )}
        </>
      ) : (
        <p className="muted-copy">{cloudIntelligenceError || "Checking service availability..."}</p>
      )}
    </Panel>
  );
}

function RuntimeCompatibilityPanel({
  runtimeSupport,
  cloudIntelligenceError,
}: {
  runtimeSupport: RuntimeSupportResult | null;
  cloudIntelligenceError: string;
}) {
  return (
    <Panel title="Runtime Compatibility">
      {runtimeSupport ? (
        <>
          <KeyValue label="Target" value={runtimeSupport.target_service} />
          <KeyValue label="Status" value={runtimeSupport.supported ? "Supported" : "Needs review"} />
          <KeyValue label="Detected" value={list(runtimeSupport.supported_runtimes)} />
          {runtimeSupport.unsupported_runtimes.length > 0 && <KeyValue label="Unsupported" value={list(runtimeSupport.unsupported_runtimes)} />}
          <div className="section-spacer">
            <div className="subsection-label">Catalog Supports</div>
            <List items={runtimeSupport.catalog_supported_runtimes} />
          </div>
          {runtimeSupport.notes.length > 0 && (
            <div className="section-spacer">
              <List items={runtimeSupport.notes} />
            </div>
          )}
        </>
      ) : (
        <p className="muted-copy">{cloudIntelligenceError || "Checking runtime compatibility..."}</p>
      )}
    </Panel>
  );
}

function CostStrategyPanel({
  assessment,
  activeRegion,
  activeMonthlyValue,
  activeRangeValue,
  activeAnnualValue,
  activeLineItems,
  activeAssumptions,
  onCompare,
}: {
  assessment: Assessment;
  activeRegion: string;
  activeMonthlyValue: string;
  activeRangeValue: string;
  activeAnnualValue: string;
  activeLineItems?: string[];
  activeAssumptions: string[];
  onCompare: () => void;
}) {
  return (
    <Panel
      title="Cost And Strategy"
      action={
        <button type="button" className="small-outline-action" onClick={onCompare}>
          Compare Regions
        </button>
      }
    >
      <KeyValue label="Provider" value={assessment.recommended_provider} />
      <KeyValue label="Strategy" value={assessment.migration_strategy} />
      <KeyValue label="Location" value={activeRegion} />
      <KeyValue label="Monthly" value={activeMonthlyValue} />
      <KeyValue label="Range" value={activeRangeValue} />
      <KeyValue label="Annual" value={activeAnnualValue} />
      <div className="section-spacer">
        <List items={activeLineItems} />
      </div>
      {activeAssumptions.length > 0 && (
        <div className="assumption-box">
          <div className="assumption-title">Pricing assumptions</div>
          <List items={activeAssumptions} />
        </div>
      )}
    </Panel>
  );
}

function overviewSummary(assessment: Assessment, riskLevel: string) {
  const stack = [
    ...(assessment.technology_stack.frameworks ?? []),
    ...(assessment.technology_stack.runtimes ?? []),
  ].slice(0, 3).join(", ") || "the detected application stack";
  const database = list(assessment.technology_stack.databases);

  return `InfraGuide analyzed ${stack} and identified a ${assessment.cloud_readiness.complexity.toLowerCase()} migration profile with ${assessment.cloud_readiness.score}% cloud readiness. The current risk level is ${riskLevel.toLowerCase()}, with ${database === "Not detected" ? "no persistent database dependency detected" : `${database} data dependencies detected`}.`;
}

function migrationDirectionSummary(assessment: Assessment, activeRegion: string, activeMonthlyValue: string) {
  return `The recommended direction is ${assessment.migration_strategy} on ${assessment.recommended_provider}, using ${activeRegion} as the current planning region. The baseline monthly estimate is ${activeMonthlyValue}, and detailed service and regional pricing validation are available in Cloud Fit.`;
}

function defaultRegion(provider: string) {
  if (provider === "Azure") return "eastus";
  if (provider === "GCP") return "us-central1";
  return "us-east-1";
}

function defaultCostRegion(assessment: Assessment) {
  const regionalPrice = assessment.cost_estimation.regional_prices?.[0]?.region;
  if (regionalPrice) {
    return regionalPrice;
  }

  const regionAssumption = assessment.cost_estimation.assumptions?.find((item) => item.toLowerCase().startsWith("azure region:"));
  if (regionAssumption) {
    return regionAssumption.split(":").slice(1).join(":").trim();
  }

  return defaultRegion(assessment.recommended_provider);
}

function applicationRuntimeService(assessment: Assessment) {
  return (
    assessment.recommended_services.find((service) => service.component.toLowerCase() === "application runtime")?.recommended ??
    assessment.recommended_services[0]?.recommended ??
    `${assessment.recommended_provider} runtime`
  );
}
