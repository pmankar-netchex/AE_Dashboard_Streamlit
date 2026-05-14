import { lazy, Suspense } from "react";
import { useColumnMeta, useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";

const PerformanceHeatmap = lazy(() =>
  import("@/components/dashboard/PerformanceHeatmap").then((m) => ({
    default: m.PerformanceHeatmap,
  })),
);

export function DashboardHeatmapRoute() {
  const { filters } = useFilters();
  const dash = useDashboard(filters);
  const cols = useColumnMeta();

  if (dash.isLoading || cols.isLoading) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        Loading heatmap…
      </div>
    );
  }
  if (!dash.data || !cols.data || dash.data.rows.length === 0) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        No data to render heatmap.
      </div>
    );
  }

  return (
    <Suspense
      fallback={
        <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
          Loading heatmap…
        </div>
      }
    >
      <PerformanceHeatmap rows={dash.data.rows} columns={cols.data.columns} />
    </Suspense>
  );
}
