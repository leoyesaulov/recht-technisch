import { API_BASE_URL } from "../config";

export type StatItem = {
  id: string;
  value: number;
  percentage?: number;
};

export type MonthlyVolumeStats = {
  updated_at: string;
  total_complaints: number;
  monthly_volume: { period: string; value: number }[];
};

export type ChartsStats = {
  updated_at: string;
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
    throw new Error(error?.error ?? error?.detail ?? "Dieser Bereich des Dashboards konnte nicht geladen werden.");
  }
  return response.json();
}

export type IngestionResult = { inserted: number };

export async function uploadComplaints(file: File, signal?: AbortSignal): Promise<IngestionResult> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/ingestion`, { method: "POST", body: formData, signal });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.error ?? error?.detail ?? "Die Datei konnte nicht verarbeitet werden.");
  }
  return response.json();
}

export function getMonthlyVolumeStats(signal?: AbortSignal) {
  return get<MonthlyVolumeStats>("/descriptive-stats/monthly-volume", signal);
}

export function getChartsStats(signal?: AbortSignal) {
  return get<ChartsStats>("/descriptive-stats/charts", signal);
}

export function getClusters(signal?: AbortSignal) {
  return get<Cluster[]>("/clusters", signal);
}

export function getRecommendations(signal?: AbortSignal) {
  return get<Recommendation[]>("/recommendations", signal);
}
