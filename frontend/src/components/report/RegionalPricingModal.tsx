import React from "react";
import { Loader2, X } from "lucide-react";
import { KeyValue } from "@/components/ui/common";
import { responseErrorMessage } from "@/lib/api/assessments";
import { fetchRegionalPricing } from "@/lib/api/pricing";
import { pricingRegions } from "@/lib/constants";
import type { RegionalPrice, ServiceRecommendation } from "@/lib/types";

export function RegionalPricingModal({
  provider,
  initialPrices,
  cloudSizing,
  services,
  appliedRegion,
  onApply,
  onClose,
}: {
  provider: string;
  initialPrices: RegionalPrice[];
  cloudSizing?: { cpu_cores?: number; memory_gb?: number } | null;
  services: ServiceRecommendation[];
  appliedRegion: RegionalPrice | null;
  onApply: (price: RegionalPrice) => void;
  onClose: () => void;
}) {
  const [prices, setPrices] = React.useState<RegionalPrice[]>(initialPrices);
  const [selectedRegion, setSelectedRegion] = React.useState<RegionalPrice | null>(appliedRegion ?? initialPrices[0] ?? null);
  const [isLoadingRegions, setIsLoadingRegions] = React.useState(initialPrices.length === 0 && ["AWS", "Azure", "GCP"].includes(provider));
  const [regionalError, setRegionalError] = React.useState("");
  const [selectedPricingRegion, setSelectedPricingRegion] = React.useState("");
  const [hasLoadedRegionList, setHasLoadedRegionList] = React.useState(initialPrices.length > 0);
  const availableRegions = pricingRegions[provider] ?? [];
  const tableCurrency = selectedRegion?.currency ?? prices[0]?.currency ?? "";

  React.useEffect(() => {
    if (!["AWS", "Azure", "GCP"].includes(provider)) {
      return;
    }

    let isActive = true;

    async function loadRegionalPricing() {
      setIsLoadingRegions(true);
      setRegionalError("");

      try {
        const response = await fetchRegionalPricing({
          provider,
          cpu: cloudSizing?.cpu_cores ?? 2,
          memory: cloudSizing?.memory_gb ?? 4,
          limit: selectedPricingRegion ? 1 : 10,
          region: selectedPricingRegion || undefined,
          services,
        });

        if (!response.ok) {
          throw new Error(await responseErrorMessage(response));
        }

        const data = await response.json();
        const rows = data.regions ?? [];

        if (isActive) {
          setPrices(rows);
          setSelectedRegion((current) => rows.find((row: RegionalPrice) => row.region === current?.region) ?? rows[0] ?? null);
          if (!selectedPricingRegion && rows.length > 0) {
            setHasLoadedRegionList(true);
          }
        }
      } catch (caught) {
        if (isActive) {
          setRegionalError(caught instanceof Error ? caught.message : "Regional pricing failed");
        }
      } finally {
        if (isActive) {
          setIsLoadingRegions(false);
        }
      }
    }

    loadRegionalPricing();

    return () => {
      isActive = false;
    };
  }, [cloudSizing?.cpu_cores, cloudSizing?.memory_gb, initialPrices, provider, selectedPricingRegion, services]);

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel regional-pricing-modal" role="dialog" aria-modal="true" aria-labelledby="regionalPricingTitle">
        <div className="pricing-modal-header">
          <div className="pricing-modal-title-row">
            <div>
              <h2 id="regionalPricingTitle" className="modal-title">
                {provider} regional pricing
              </h2>
              <p className="modal-subtitle">Monthly estimate by region for runtime and recommended services.</p>
            </div>
            {availableRegions.length > 0 && (
              <label className="pricing-region-field">
                <span className="field-label">Location</span>
                <select className="input" value={selectedPricingRegion} onChange={(event) => setSelectedPricingRegion(event.target.value)} disabled={!hasLoadedRegionList || isLoadingRegions}>
                  <option value="">Available regions</option>
                  {availableRegions.map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          <button type="button" className="clear-folder-button" onClick={onClose} aria-label="Close regional pricing dialog">
            <X size={16} />
          </button>
        </div>

        {isLoadingRegions ? (
          <div className="pricing-loading">
            <div className="pricing-loading-content">
              <Loader2 className="pricing-loading-icon animate-spin" size={34} aria-hidden="true" />
              <div className="pricing-loading-title">Loading {provider} regional pricing</div>
              <div className="pricing-loading-copy">Fetching provider catalog and service SKU costs.</div>
            </div>
          </div>
        ) : regionalError ? (
          <div className="pricing-error">{regionalError}</div>
        ) : prices.length > 0 ? (
          <div className="pricing-grid">
            <div className="pricing-table-wrap">
              <table className="pricing-table">
                <thead className="pricing-table-head">
                  <tr>
                    <th className="pricing-col-region">Region</th>
                    <th className="pricing-col-runtime">Runtime SKU</th>
                    <th className="pricing-col-money">Runtime{tableCurrency ? ` (${tableCurrency})` : ""}</th>
                    <th className="pricing-col-services">Services Total{tableCurrency ? ` (${tableCurrency})` : ""}</th>
                    <th className="pricing-col-money">Total{tableCurrency ? ` (${tableCurrency})` : ""}</th>
                    <th className="pricing-col-source">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.map((price) => {
                    const isSelected = selectedRegion?.region === price.region;

                    return (
                      <tr key={`${price.provider ?? provider}-${price.region}`} className={`pricing-row ${isSelected ? "pricing-row-selected" : ""}`} onClick={() => setSelectedRegion(price)}>
                        <td className="pricing-region-cell">{price.region}</td>
                        <td className="pricing-text-cell">{price.runtime_sku || "Runtime"}</td>
                        <td className="pricing-money-cell">{formatAmount(price.runtime_monthly)}</td>
                        <td className="pricing-money-cell">{formatAmount(price.services_monthly)}</td>
                        <td className="pricing-total-cell">{formatAmount(price.total_monthly)}</td>
                        <td className="pricing-source-cell">{price.source ?? "Pricing API"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <RegionServiceBreakdown price={selectedRegion} appliedRegion={appliedRegion} onApply={onApply} />
          </div>
        ) : (
          <div className="pricing-empty">
            Regional pricing rows were not returned for this assessment. Regenerate the blueprint after restarting the backend, MCP server, and bridge so the latest regional pricing endpoints are active.
          </div>
        )}
      </section>
    </div>
  );
}

function RegionServiceBreakdown({
  price,
  appliedRegion,
  onApply,
}: {
  price: RegionalPrice | null;
  appliedRegion: RegionalPrice | null;
  onApply: (price: RegionalPrice) => void;
}) {
  if (!price) {
    return <aside className="pricing-breakdown-empty">Select a region to view service costs.</aside>;
  }

  return (
    <aside className="pricing-breakdown">
      <div className="pricing-breakdown-header">
        <h3 className="pricing-breakdown-title">{price.region}</h3>
        <p className="pricing-breakdown-copy">Service cost breakdown for this region.</p>
      </div>

      <KeyValue label={`Runtime (${price.currency})`} value={formatAmount(price.runtime_monthly)} />
      <KeyValue label={`Services Total (${price.currency})`} value={formatAmount(price.services_monthly)} />
      <KeyValue label={`Total (${price.currency})`} value={formatAmount(price.total_monthly)} />
      <div className="section-spacer">
        <button
          type="button"
          className="pricing-apply-button"
          onClick={() => onApply(price)}
          disabled={appliedRegion?.region === price.region && appliedRegion.total_monthly === price.total_monthly}
        >
          {appliedRegion?.region === price.region && appliedRegion.total_monthly === price.total_monthly ? "Migration location updated" : "Update location to migration"}
        </button>
      </div>

      <div className="service-list section-spacer">
        {(price.service_breakdown ?? []).length > 0 ? (
          price.service_breakdown?.map((service) => (
            <div key={`${price.region}-${service.component}`} className="service-cost-item">
              <div className="service-cost-row">
                <div>
                  <div className="service-title">{service.component}</div>
                  {service.recommended && <div className="service-subtitle">{service.recommended}</div>}
                </div>
                <div className="service-cost">${formatAmount(service.monthly_cost)}</div>
              </div>
            </div>
          ))
        ) : (
          <div className="pricing-empty">
            Per-service rows were not returned for this region. Regenerate the assessment after restarting MCP and bridge so the latest service breakdown response is active.
          </div>
        )}
      </div>
    </aside>
  );
}

function formatAmount(amount: number) {
  return amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
