import { FilterBar } from "@/components/filters/FilterBar";
import { AllSourceSummary } from "@/components/dashboard/AllSourceSummary";
import { AttainmentBarChart } from "@/components/dashboard/AttainmentBarChart";
import { BookingsBarChart } from "@/components/dashboard/BookingsBarChart";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { PerformanceHeatmap } from "@/components/dashboard/PerformanceHeatmap";
import { SectionTable } from "@/components/dashboard/SectionTable";
import { AEDrillDownDrawer } from "@/components/drawer/AEDrillDownDrawer";
import { useColumnMeta, useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";

export function DashboardRoute() {
  const { filters } = useFilters();
  const cols = useColumnMeta();
  const dash = useDashboard(filters);

  return (
    <div className="-mx-6 -mt-6">
      <FilterBar />
      <div className="space-y-6 p-6">
        {dash.isError && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
            Failed to load dashboard: {(dash.error as Error).message}
          </div>
        )}

        {dash.data && cols.data && (
          <AllSourceSummary
            rows={dash.data.all_source_summary}
            sources={cols.data.all_source_summary}
          />
        )}

        {dash.data && (
          <KpiRow row1={dash.data.kpi_row_1} row2={dash.data.kpi_row_2} />
        )}

        {dash.data && cols.data && (
          <div className="space-y-3">
            {cols.data.sections.map((section) => (
              <SectionTable
                key={section.key}
                section={section}
                columns={cols.data!.columns.filter(
                  (c) => c.section === section.key,
                )}
                rows={dash.data!.rows}
                defaultOpen={false}
              />
            ))}
          </div>
        )}

        {dash.data && dash.data.rows.length > 0 && (
          <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <BookingsBarChart rows={dash.data.rows} />
            <AttainmentBarChart rows={dash.data.rows} />
          </section>
        )}

        {dash.data && cols.data && dash.data.rows.length > 0 && (
          <PerformanceHeatmap rows={dash.data.rows} columns={cols.data.columns} />
        )}

        {(dash.isLoading || cols.isLoading) && (
          <div className="rounded-lg border border-border bg-background p-6 text-sm text-muted-foreground">
            Loading dashboard…
          </div>
        )}
      </div>
      <AEDrillDownDrawer />
    </div>
  );
}
