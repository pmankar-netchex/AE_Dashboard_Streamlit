import type { KpiValue } from "@/types/dashboard";
import { fmt } from "@/lib/formatters";

export function KpiCard({ kpi }: { kpi: KpiValue }) {
  return (
    <div className="rounded-lg border border-border bg-background px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {kpi.display_name}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums">
        {fmt(kpi.value, kpi.format)}
      </div>
    </div>
  );
}
