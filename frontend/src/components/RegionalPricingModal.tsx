import React from "react";
import { X } from "lucide-react";
import { pricingRegions } from "../constants";
import { fetchRegionalPricing } from "../api/pricing";
import { responseErrorMessage } from "../api/assessments";
import type { RegionalPrice, ServiceRecommendation } from "../types";
import { KeyValue } from "./common";

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
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 id="regionalPricingTitle" className="text-xl font-semibold">
                {provider} regional pricing
              </h2>
              <p className="mt-1 text-sm text-ink/65">Monthly estimate by region for runtime and recommended services.</p>
            </div>
            {availableRegions.length > 0 && (
              <label className="w-full sm:w-64">
                <span className="field-label">Location</span>
                <select className="input" value={selectedPricingRegion} onChange={(event) => setSelectedPricingRegion(event.target.value)} disabled={!hasLoadedRegionList || isLoadingRegions}>
                  <option value="">Top 10 regions</option>
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
          <div className="rounded-md border border-ink/10 bg-cloud p-4 text-sm leading-6 text-ink/70">
            Loading regional pricing from {provider}. This can take a little longer when the provider pricing catalog is paged by service and SKU.
          </div>
        ) : regionalError ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">{regionalError}</div>
        ) : prices.length > 0 ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
            <div className="overflow-x-hidden overflow-y-auto rounded-md border border-ink/10">
              <table className="w-full table-fixed border-collapse text-left text-sm">
                <thead className="bg-cloud text-xs uppercase text-ink/60">
                  <tr>
                    <th className="w-[23%] px-3 py-3 font-bold">Region</th>
                    <th className="w-[20%] px-3 py-3 font-bold">Runtime SKU</th>
                    <th className="w-[14%] px-3 py-3 text-right font-bold">Runtime{tableCurrency ? ` (${tableCurrency})` : ""}</th>
                    <th className="w-[16%] px-3 py-3 text-right font-bold">Services Total{tableCurrency ? ` (${tableCurrency})` : ""}</th>
                    <th className="w-[14%] px-3 py-3 text-right font-bold">Total{tableCurrency ? ` (${tableCurrency})` : ""}</th>
                    <th className="w-[13%] px-3 py-3 font-bold">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.map((price) => {
                    const isSelected = selectedRegion?.region === price.region;

                    return (
                      <tr key={`${price.provider ?? provider}-${price.region}`} className={`cursor-pointer border-t border-ink/10 transition hover:bg-cloud ${isSelected ? "bg-cloud" : ""}`} onClick={() => setSelectedRegion(price)}>
                        <td className="break-words px-3 py-3 font-semibold text-moss">{price.region}</td>
                        <td className="break-words px-3 py-3 text-ink/70">{price.runtime_sku || "Runtime"}</td>
                        <td className="px-3 py-3 text-right">{formatAmount(price.runtime_monthly)}</td>
                        <td className="px-3 py-3 text-right">{formatAmount(price.services_monthly)}</td>
                        <td className="px-3 py-3 text-right font-bold">{formatAmount(price.total_monthly)}</td>
                        <td className="break-words px-3 py-3 text-ink/65">{price.source ?? "Pricing API"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <RegionServiceBreakdown price={selectedRegion} appliedRegion={appliedRegion} onApply={onApply} />
          </div>
        ) : (
          <div className="rounded-md border border-ink/10 bg-cloud p-4 text-sm leading-6 text-ink/70">
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
    return <aside className="rounded-md border border-ink/10 bg-cloud p-4 text-sm text-ink/65">Select a region to view service costs.</aside>;
  }

  return (
    <aside className="rounded-md border border-ink/10 p-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{price.region}</h3>
        <p className="mt-1 text-sm text-ink/65">Service cost breakdown for this region.</p>
      </div>

      <KeyValue label={`Runtime (${price.currency})`} value={formatAmount(price.runtime_monthly)} />
      <KeyValue label={`Services Total (${price.currency})`} value={formatAmount(price.services_monthly)} />
      <KeyValue label={`Total (${price.currency})`} value={formatAmount(price.total_monthly)} />
      <div className="mt-4">
        <button
          type="button"
          className="flex w-full items-center justify-center rounded-md bg-moss px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => onApply(price)}
          disabled={appliedRegion?.region === price.region && appliedRegion.total_monthly === price.total_monthly}
        >
          {appliedRegion?.region === price.region && appliedRegion.total_monthly === price.total_monthly ? "Migration location updated" : "Update location to migration"}
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {(price.service_breakdown ?? []).length > 0 ? (
          price.service_breakdown?.map((service) => (
            <div key={`${price.region}-${service.component}`} className="rounded-md bg-cloud p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-semibold">{service.component}</div>
                  {service.recommended && <div className="mt-1 text-xs leading-5 text-ink/60">{service.recommended}</div>}
                </div>
                <div className="text-right font-bold">{formatAmount(service.monthly_cost)}</div>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-md bg-cloud p-3 text-sm leading-6 text-ink/65">
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
