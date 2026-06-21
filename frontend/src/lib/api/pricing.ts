import { API_BASE_URL } from "@/lib/constants";
import type { ServiceRecommendation } from "@/lib/types";

export function fetchRegionalPricing({
  provider,
  cpu,
  memory,
  limit,
  region,
  services,
}: {
  provider: string;
  cpu: number;
  memory: number;
  limit: number;
  region?: string;
  services: ServiceRecommendation[];
}) {
  return fetch(`${API_BASE_URL}/pricing/regions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider,
      cpu,
      memory,
      limit,
      region,
      services: services
        .filter((service) => service.component !== "Application Runtime")
        .map((service) => ({
          component: service.component,
          recommended: service.recommended,
          current: service.current,
        })),
    }),
  });
}
