import type {
  AEDrillDownResponse,
  AEOption,
  ColumnsResponse,
  DashboardResponse,
  ManagerOption,
  TimePresetOption,
} from "@/types/dashboard";
import type { FilterState } from "@/types/filters";
import { api } from "./client";

function dashboardQuery(filters: FilterState): string {
  const sp = new URLSearchParams();
  if (filters.manager) sp.set("manager", filters.manager);
  if (filters.aeIds.length === 1) sp.set("ae", filters.aeIds[0]);
  if (filters.period) sp.set("period", filters.period);
  if (filters.period === "custom") {
    if (filters.from) sp.set("from", filters.from);
    if (filters.to) sp.set("to", filters.to);
  }
  const q = sp.toString();
  return q ? `?${q}` : "";
}

export function fetchColumns(): Promise<ColumnsResponse> {
  return api<ColumnsResponse>("/api/columns");
}

export function fetchDashboard(filters: FilterState): Promise<DashboardResponse> {
  return api<DashboardResponse>(`/api/dashboard${dashboardQuery(filters)}`);
}

export function fetchAeDrillDown(
  aeId: string,
  filters: FilterState,
): Promise<AEDrillDownResponse> {
  return api<AEDrillDownResponse>(`/api/dashboard/ae/${encodeURIComponent(aeId)}${dashboardQuery(filters)}`);
}

export function fetchManagers(): Promise<ManagerOption[]> {
  return api<ManagerOption[]>("/api/filters/managers");
}

export function fetchAes(manager: string | null): Promise<AEOption[]> {
  const q = manager ? `?manager=${encodeURIComponent(manager)}` : "";
  return api<AEOption[]>(`/api/filters/aes${q}`);
}

export function fetchTimePresets(): Promise<TimePresetOption[]> {
  return api<TimePresetOption[]>("/api/filters/time-presets");
}
