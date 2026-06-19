import React from "react";
import { ArrowDownToLine } from "lucide-react";
import { fetchRuntimeSupport, fetchServiceAvailability, parseRuntimeSupport, parseServiceAvailability } from "../api/cloudIntelligence";
import type { Assessment, RegionalPrice, RuntimeSupportResult, ServiceAvailabilityResult } from "../types";
import { formatMoney, list } from "../utils/format";
import { KeyValue, List, Panel } from "./common";
import { RegionalPricingModal } from "./RegionalPricingModal";

export function Report({ assessment, onDownload }: { assessment: Assessment; onDownload: () => void }) {
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
      <div className="mb-5 flex flex-col gap-3 border-b border-ink/10 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Migration Blueprint</h2>
          <p className="mt-1 text-sm text-ink/65">{assessment.architecture_summary}</p>
        </div>
        <button onClick={onDownload} className="flex items-center justify-center gap-2 rounded-md border border-moss px-4 py-2 font-semibold text-moss transition hover:bg-moss hover:text-white">
          <ArrowDownToLine size={18} />
          Download
        </button>
      </div>

      <div className="report-card-flow">
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

        <Panel title="Cloud Service Validation">
          {serviceAvailability ? (
            <>
              <KeyValue label="Region" value={serviceAvailability.region} />
              <KeyValue label="Catalog" value={`${serviceAvailability.catalog_source ?? "catalog"} ${serviceAvailability.catalog_version ?? ""}`.trim()} />
              <KeyValue label="Region Support" value={serviceAvailability.region_supported ? "Supported" : "Not supported"} />
              <div className="mt-4">
                <div className="mb-2 text-sm font-semibold text-ink/70">Available Services</div>
                <List items={serviceAvailability.available.map((item) => `${item.component ?? item.category}: ${item.service}`)} />
              </div>
              {serviceAvailability.unavailable.length > 0 && (
                <div className="mt-4">
                  <div className="mb-2 text-sm font-semibold text-ink/70">Needs Review</div>
                  <List items={serviceAvailability.unavailable.map((item) => `${item.component ?? item.category}: ${item.service}`)} />
                </div>
              )}
              {serviceAvailability.notes.length > 0 && (
                <div className="mt-4">
                  <List items={serviceAvailability.notes} />
                </div>
              )}
            </>
          ) : (
            <p className="text-sm leading-6 text-ink/65">{cloudIntelligenceError || "Checking service availability..."}</p>
          )}
        </Panel>

        <Panel title="Runtime Compatibility">
          {runtimeSupport ? (
            <>
              <KeyValue label="Target" value={runtimeSupport.target_service} />
              <KeyValue label="Status" value={runtimeSupport.supported ? "Supported" : "Needs review"} />
              <KeyValue label="Detected" value={list(runtimeSupport.supported_runtimes)} />
              {runtimeSupport.unsupported_runtimes.length > 0 && <KeyValue label="Unsupported" value={list(runtimeSupport.unsupported_runtimes)} />}
              <div className="mt-4">
                <div className="mb-2 text-sm font-semibold text-ink/70">Catalog Supports</div>
                <List items={runtimeSupport.catalog_supported_runtimes} />
              </div>
              {runtimeSupport.notes.length > 0 && (
                <div className="mt-4">
                  <List items={runtimeSupport.notes} />
                </div>
              )}
            </>
          ) : (
            <p className="text-sm leading-6 text-ink/65">{cloudIntelligenceError || "Checking runtime compatibility..."}</p>
          )}
        </Panel>

        <Panel
          title="Cost And Strategy"
          action={
            <button type="button" className="rounded-md border border-moss px-3 py-1.5 text-sm font-semibold text-moss transition hover:bg-moss hover:text-white disabled:cursor-not-allowed disabled:opacity-50" onClick={() => setIsPricingModalOpen(true)}>
              Compare and select
            </button>
          }
        >
          <KeyValue label="Provider" value={assessment.recommended_provider} />
          <KeyValue label="Strategy" value={assessment.migration_strategy} />
          <KeyValue label="Location" value={activeRegion} />
          <KeyValue label="Monthly" value={activeMonthlyValue} />
          <KeyValue label="Range" value={activeRangeValue} />
          <KeyValue label="Annual" value={activeAnnualValue} />
          <div className="mt-4">
            <List items={activeLineItems} />
          </div>
        </Panel>

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

      {assessment.warnings.length > 0 && <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{assessment.warnings.join(" ")}</div>}

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
