import { useQuery } from "@tanstack/react-query";
import {
  fetchAeDrillDown,
  fetchAes,
  fetchColumns,
  fetchDashboard,
  fetchManagers,
  fetchTimePresets,
} from "@/api/dashboard";
import { stableKey } from "@/lib/filterParams";
import type {
  AEDrillDownResponse,
  AEOption,
  ColumnsResponse,
  DashboardResponse,
  ManagerOption,
  TimePresetOption,
} from "@/types/dashboard";
import type { FilterState } from "@/types/filters";

export function useColumnMeta() {
  return useQuery<ColumnsResponse>({
    queryKey: ["columns"],
    queryFn: fetchColumns,
    staleTime: 10 * 60_000,
  });
}

export function useDashboard(filters: FilterState) {
  return useQuery<DashboardResponse>({
    queryKey: ["dashboard", stableKey(filters)],
    queryFn: () => fetchDashboard(filters),
    staleTime: 30_000,
  });
}

export function useAeDetail(aeId: string | null, filters: FilterState) {
  return useQuery<AEDrillDownResponse>({
    queryKey: ["ae-detail", aeId, stableKey(filters)],
    queryFn: () => fetchAeDrillDown(aeId as string, filters),
    enabled: !!aeId,
    staleTime: 30_000,
  });
}

export function useManagers() {
  return useQuery<ManagerOption[]>({
    queryKey: ["filters", "managers"],
    queryFn: fetchManagers,
    staleTime: 5 * 60_000,
  });
}

export function useAes(manager: string | null) {
  return useQuery<AEOption[]>({
    queryKey: ["filters", "aes", manager],
    queryFn: () => fetchAes(manager),
    staleTime: 5 * 60_000,
  });
}

export function useTimePresets() {
  return useQuery<TimePresetOption[]>({
    queryKey: ["filters", "time-presets"],
    queryFn: fetchTimePresets,
    staleTime: 30 * 60_000,
  });
}
