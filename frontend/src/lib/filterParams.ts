import { DEFAULT_FILTER_STATE, type FilterState } from "@/types/filters";
import type { TimePreset } from "@/types/dashboard";

const PRESETS: TimePreset[] = [
  "this_week",
  "last_week",
  "this_month",
  "last_month",
  "custom",
];

export interface FilterSearch {
  manager?: string;
  ae?: string[];
  period?: string;
  from?: string;
  to?: string;
  aeDrillId?: string;
}

export function searchToFilters(search: FilterSearch): FilterState {
  const period: TimePreset = PRESETS.includes(search.period as TimePreset)
    ? (search.period as TimePreset)
    : DEFAULT_FILTER_STATE.period;
  const aeIds = Array.isArray(search.ae)
    ? search.ae
    : search.ae
      ? [search.ae]
      : [];
  return {
    manager: search.manager ?? null,
    aeIds,
    period,
    from: search.from ?? null,
    to: search.to ?? null,
    aeDrillId: search.aeDrillId ?? null,
  };
}

export function filtersToSearch(filters: FilterState): FilterSearch {
  const out: FilterSearch = {};
  if (filters.manager) out.manager = filters.manager;
  if (filters.aeIds.length > 0) out.ae = filters.aeIds;
  if (filters.period !== DEFAULT_FILTER_STATE.period) out.period = filters.period;
  if (filters.from) out.from = filters.from;
  if (filters.to) out.to = filters.to;
  if (filters.aeDrillId) out.aeDrillId = filters.aeDrillId;
  return out;
}

export function stableKey(filters: FilterState): string {
  const sorted = [...filters.aeIds].sort();
  return JSON.stringify({
    manager: filters.manager ?? "",
    ae: sorted,
    period: filters.period,
    from: filters.from ?? "",
    to: filters.to ?? "",
  });
}
