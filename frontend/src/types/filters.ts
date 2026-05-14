import type { TimePreset } from "./dashboard";

export interface FilterState {
  manager: string | null;
  aeIds: string[];
  period: TimePreset;
  from: string | null;
  to: string | null;
  aeDrillId: string | null;
}

export const DEFAULT_FILTER_STATE: FilterState = {
  manager: null,
  aeIds: [],
  period: "this_month",
  from: null,
  to: null,
  aeDrillId: null,
};
