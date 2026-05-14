import { useFilters } from "@/hooks/useFilters";
import { cn } from "@/lib/cn";
import type { TimePreset } from "@/types/dashboard";

const PRESETS: { key: TimePreset; label: string }[] = [
  { key: "this_week", label: "This Wk" },
  { key: "last_week", label: "Last Wk" },
  { key: "this_month", label: "This Mo" },
  { key: "last_month", label: "Last Mo" },
  { key: "custom", label: "Custom" },
];

export function TimePeriodPicker() {
  const { filters, set } = useFilters();
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">Period</span>
      <div className="inline-flex overflow-hidden rounded-md border border-border">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => set({ period: p.key })}
            className={cn(
              "px-2.5 py-1 text-xs",
              filters.period === p.key
                ? "bg-primary text-primary-foreground"
                : "bg-background hover:bg-accent",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      {filters.period === "custom" && (
        <div className="flex items-center gap-1 text-xs">
          <input
            type="date"
            className="h-8 rounded-md border border-border bg-background px-1"
            value={filters.from ?? ""}
            onChange={(e) => set({ from: e.target.value || null })}
          />
          <span className="text-muted-foreground">–</span>
          <input
            type="date"
            className="h-8 rounded-md border border-border bg-background px-1"
            value={filters.to ?? ""}
            onChange={(e) => set({ to: e.target.value || null })}
          />
        </div>
      )}
    </div>
  );
}
