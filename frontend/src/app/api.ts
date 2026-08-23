import { API_BASE_URL } from "../config";

export type StatItem = {
  id: string;
  value: number;
  percentage?: number;
};

export type DescriptiveStats = {
  updated_at: string;
  total_complaints: number;
  monthly_volume: { period: string; value: number }[];
  severity: StatItem[];
  channels: StatItem[];
  retailers: StatItem[];
};

export type Cluster = {
  id: string;
  title: string;
  text: string;
  count: number;
};

export type RecommendationId = "political" | "focus" | "user_warning";

export type Recommendation = {
  id: RecommendationId;
  text: string;
  detail: string;
};

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.error ?? "Dieser Bereich des Dashboards konnte nicht geladen werden.");
  }
  return response.json();
}

export function getDescriptiveStats(signal?: AbortSignal) {
  return get<DescriptiveStats>("/descriptive-stats", signal);
}

export function getClusters(signal?: AbortSignal) {
  return get<Cluster[]>("/clusters", signal);
}

export function getRecommendations(signal?: AbortSignal) {
  return get<Recommendation[]>("/recommendations", signal);
}
