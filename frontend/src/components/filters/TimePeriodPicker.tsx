import { Check, Calendar } from "lucide-react";
import { useState } from "react";
import { FilterChip } from "./FilterChip";
import { useFilters } from "@/hooks/useFilters";
import { cn } from "@/lib/cn";
import type { TimePreset } from "@/types/dashboard";

const PRESETS: { key: TimePreset; label: string }[] = [
  { key: "this_week", label: "This week" },
  { key: "last_week", label: "Last week" },
  { key: "this_month", label: "This month" },
  { key: "last_month", label: "Last month" },
  { key: "custom", label: "Custom range" },
];

function presetLabel(key: TimePreset, from: string | null, to: string | null): string {
  if (key === "custom" && from && to) return `${from} → ${to}`;
  if (key === "custom") return "Custom range";
  return PRESETS.find((p) => p.key === key)?.label ?? "This month";
}

export function TimePeriodPicker() {
  const { filters, set } = useFilters();
  const [draftFrom, setDraftFrom] = useState(filters.from ?? "");
  const [draftTo, setDraftTo] = useState(filters.to ?? "");
  const isDefault = filters.period === "this_month";
  const showCustomInputs = filters.period === "custom";

  return (
    <FilterChip
      label="Period"
      value={presetLabel(filters.period, filters.from, filters.to)}
      active={!isDefault}
      popoverWidthClass="w-72"
    >
      {({ close }) => (
        <div className="flex flex-col gap-1">
          <ul className="flex flex-col">
            {PRESETS.map((p) => {
              const active = filters.period === p.key;
              return (
                <li key={p.key}>
                  <button
                    type="button"
                    onClick={() => {
                      if (p.key !== "custom") {
                        set({ period: p.key, from: null, to: null });
                        close();
                      } else {
                        set({ period: "custom" });
                        // keep popover open so user can pick dates
                      }
                    }}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent",
                      active && "bg-accent",
                    )}
                  >
                    <span className="inline-flex items-center gap-2">
                      {p.key === "custom" && (
                        <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                      {p.label}
                    </span>
                    {active && <Check className="h-3.5 w-3.5 text-foreground" />}
                  </button>
                </li>
              );
            })}
          </ul>

          {showCustomInputs && (
            <div className="mt-1 space-y-2 border-t border-border pt-2">
              <label className="block text-[11px] text-muted-foreground">
                From
                <input
                  type="date"
                  value={draftFrom}
                  onChange={(e) => setDraftFrom(e.target.value)}
                  className="mt-1 block h-8 w-full rounded-md border border-border bg-background px-2 text-sm"
                />
              </label>
              <label className="block text-[11px] text-muted-foreground">
                To
                <input
                  type="date"
                  value={draftTo}
                  onChange={(e) => setDraftTo(e.target.value)}
                  className="mt-1 block h-8 w-full rounded-md border border-border bg-background px-2 text-sm"
                />
              </label>
              <button
                type="button"
                disabled={!draftFrom || !draftTo}
                onClick={() => {
                  set({ period: "custom", from: draftFrom, to: draftTo });
                  close();
                }}
                className="h-8 w-full rounded-md bg-primary text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                Apply range
              </button>
            </div>
          )}
        </div>
      )}
    </FilterChip>
  );
}
