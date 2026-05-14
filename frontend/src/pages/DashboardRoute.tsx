import { Outlet } from "@tanstack/react-router";
import { DashboardTabs } from "@/components/dashboard/DashboardTabs";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { AEDrillDownDrawer } from "@/components/drawer/AEDrillDownDrawer";
import { FilterBar } from "@/components/filters/FilterBar";
import { useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";

export function DashboardRoute() {
  const { filters } = useFilters();
  const dash = useDashboard(filters);

  return (
    <div className="-mx-6 -mt-6">
      <FilterBar />
      <div className="space-y-4 p-6">
        {dash.isError && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
            Failed to load dashboard: {(dash.error as Error).message}
          </div>
        )}

        {dash.data && (
          <KpiRow row1={dash.data.kpi_row_1} row2={dash.data.kpi_row_2} />
        )}

        <DashboardTabs />

        <Outlet />
      </div>
      <AEDrillDownDrawer />
    </div>
  );
}
