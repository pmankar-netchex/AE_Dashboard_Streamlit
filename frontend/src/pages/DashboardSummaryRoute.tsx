import { AllSourceSummary } from "@/components/dashboard/AllSourceSummary";
import { useColumnMeta, useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";

export function DashboardSummaryRoute() {
  const { filters } = useFilters();
  const cols = useColumnMeta();
  const dash = useDashboard(filters);

  if (dash.isLoading || cols.isLoading) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        Loading summary…
      </div>
    );
  }

  if (!dash.data || !cols.data) return null;

  return (
    <AllSourceSummary
      rows={dash.data.all_source_summary}
      sources={cols.data.all_source_summary}
      columnMeta={cols.data.columns}
    />
  );
}
