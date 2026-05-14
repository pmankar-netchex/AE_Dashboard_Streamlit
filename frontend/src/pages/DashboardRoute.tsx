import { Outlet, useRouterState } from "@tanstack/react-router";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { AEDrillDownDrawer } from "@/components/drawer/AEDrillDownDrawer";
import { FilterBar } from "@/components/filters/FilterBar";
import { useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";
import { SECTION_DEFS } from "@/lib/sections";

interface PageMeta {
  title: string;
  subtitle?: string;
}

function pageMeta(pathname: string): PageMeta {
  if (pathname.startsWith("/dashboard/charts")) {
    return { title: "Charts", subtitle: "Bookings + attainment by AE" };
  }
  if (pathname.startsWith("/dashboard/heatmap")) {
    return { title: "Performance Heatmap", subtitle: "Per-column normalized" };
  }
  const sectionMatch = pathname.match(/^\/dashboard\/section\/([^/]+)/);
  if (sectionMatch) {
    const def = SECTION_DEFS.find((s) => s.slug === sectionMatch[1]);
    if (def) {
      return { title: def.label, subtitle: "Per-AE detail" };
    }
  }
  // /dashboard/summary or fallback
  return { title: "Summary", subtitle: "All Source Summary" };
}

export function DashboardRoute() {
  const { filters } = useFilters();
  const dash = useDashboard(filters);
  const { location } = useRouterState();
  const meta = pageMeta(location.pathname);

  return (
    <div className="-mx-6 -mt-6">
      <FilterBar title={meta.title} subtitle={meta.subtitle} />
      <div className="space-y-4 p-6">
        {dash.isError && (
          <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
            Failed to load dashboard: {(dash.error as Error).message}
          </div>
        )}

        {dash.data && (
          <KpiRow row1={dash.data.kpi_row_1} row2={dash.data.kpi_row_2} />
        )}

        <Outlet />
      </div>
      <AEDrillDownDrawer />
    </div>
  );
}
