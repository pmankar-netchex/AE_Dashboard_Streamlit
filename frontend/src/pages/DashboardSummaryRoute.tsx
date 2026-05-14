import { AllSourceSummary } from "@/components/dashboard/AllSourceSummary";
import { SectionTable } from "@/components/dashboard/SectionTable";
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
    <div className="space-y-4">
      <AllSourceSummary
        rows={dash.data.all_source_summary}
        sources={cols.data.all_source_summary}
      />
      <div className="space-y-3">
        {cols.data.sections.map((section) => (
          <SectionTable
            key={section.key}
            section={section}
            columns={cols.data!.columns.filter((c) => c.section === section.key)}
            rows={dash.data!.rows}
            defaultOpen={false}
          />
        ))}
      </div>
    </div>
  );
}
