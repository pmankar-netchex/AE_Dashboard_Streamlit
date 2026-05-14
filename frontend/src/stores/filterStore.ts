import { create } from "zustand";
import { DEFAULT_FILTER_STATE, type FilterState } from "@/types/filters";

interface FilterStore {
  filters: FilterState;
  set: (patch: Partial<FilterState>) => void;
  reset: () => void;
  hydrate: (s: FilterState) => void;
}

export const useFilterStore = create<FilterStore>((set) => ({
  filters: DEFAULT_FILTER_STATE,
  set: (patch) => set((s) => ({ filters: { ...s.filters, ...patch } })),
  reset: () => set({ filters: DEFAULT_FILTER_STATE }),
  hydrate: (s) => set({ filters: s }),
}));
