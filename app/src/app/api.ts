import { API_BASE_URL } from "../config";

export type DashboardItem = {
  id?: string;
  label?: string;
  value?: number;
  percentage?: number;
  category?: string;
  title?: string;
  detail?: string;
};

export type DashboardElement = {
  id: string;
  type: "metric" | "chart" | "breakdown" | "list" | "cluster" | "recommendations";
  title: string;
  value?: number;
  unit?: string;
  chart?: string;
  items?: DashboardItem[];
  icon?: string;
  count?: number;
  change_percentage?: number;
  trend?: "rising" | "falling" | "stable";
  quote?: string | null;
};

export type Dashboard = {
  id: string;
  title: string;
  period: { from: string; to: string };
  updated_at: string;
  elements: DashboardElement[];
};

export async function getDashboard(signal?: AbortSignal): Promise<Dashboard> {
  const response = await fetch(`${API_BASE_URL}/dashboard`, { signal });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.error ?? "Could not load the dashboard.");
  }

  return response.json();
}
