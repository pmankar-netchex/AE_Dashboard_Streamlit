import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect } from "react";
import { useFilterStore } from "@/stores/filterStore";
import { filtersToSearch, searchToFilters } from "@/lib/filterParams";
import type { FilterState } from "@/types/filters";

/**
 * URL search params are the source of truth. The zustand store mirrors them
 * for ergonomic reads from cells/buttons. Writes go to the URL, which then
 * re-hydrates the store.
 */
export function useFilters(): {
  filters: FilterState;
  set: (patch: Partial<FilterState>) => void;
  reset: () => void;
} {
  // useSearch from the dashboard route — guarded for routes without filter params
  const search = useSearch({ strict: false }) as Record<string, unknown>;
  const navigate = useNavigate();
  const filters = useFilterStore((s) => s.filters);
  const hydrate = useFilterStore((s) => s.hydrate);

  useEffect(() => {
    const next = searchToFilters({
      manager: typeof search.manager === "string" ? search.manager : undefined,
      ae: Array.isArray(search.ae)
        ? (search.ae as string[])
        : typeof search.ae === "string"
          ? [search.ae as string]
          : undefined,
      period: typeof search.period === "string" ? search.period : undefined,
      from: typeof search.from === "string" ? search.from : undefined,
      to: typeof search.to === "string" ? search.to : undefined,
      aeDrillId: typeof search.aeDrillId === "string" ? search.aeDrillId : undefined,
    });
    hydrate(next);
  }, [search, hydrate]);

  const set = (patch: Partial<FilterState>): void => {
    const merged = { ...filters, ...patch };
    void navigate({
      to: ".",
      search: () => filtersToSearch(merged),
      replace: true,
    });
  };

  const reset = (): void => {
    void navigate({ to: ".", search: () => ({}), replace: true });
  };

  return { filters, set, reset };
}
