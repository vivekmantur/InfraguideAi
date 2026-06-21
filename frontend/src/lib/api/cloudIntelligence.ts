import { API_BASE_URL } from "@/lib/constants";
import type { RuntimeSupportResult, ServiceAvailabilityResult, ServiceRecommendation } from "@/lib/types";

export function fetchServiceAvailability({
  provider,
  region,
  services,
}: {
  provider: string;
  region: string;
  services: ServiceRecommendation[];
}) {
  return fetch(`${API_BASE_URL}/cloud-intelligence/service-availability`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider,
      region,
      services: services.map((service) => ({
        component: service.component,
        recommended: service.recommended,
        current: service.current,
      })),
    }),
  });
}

export function fetchRuntimeSupport({
  provider,
  targetService,
  runtimes,
  frameworks,
}: {
  provider: string;
  targetService: string;
  runtimes: string[];
  frameworks: string[];
}) {
  return fetch(`${API_BASE_URL}/cloud-intelligence/runtime-support`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      provider,
      target_service: targetService,
      runtimes,
      frameworks,
    }),
  });
}

export async function parseServiceAvailability(response: Response): Promise<ServiceAvailabilityResult> {
  if (!response.ok) {
    throw new Error(`Service availability failed with status ${response.status}`);
  }
  return response.json();
}

export async function parseRuntimeSupport(response: Response): Promise<RuntimeSupportResult> {
  if (!response.ok) {
    throw new Error(`Runtime support failed with status ${response.status}`);
  }
  return response.json();
}
