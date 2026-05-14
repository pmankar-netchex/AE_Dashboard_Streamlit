import { lazy, Suspense } from "react";
import { useDashboard } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";

const BookingsBarChart = lazy(() =>
  import("@/components/dashboard/BookingsBarChart").then((m) => ({
    default: m.BookingsBarChart,
  })),
);
const AttainmentBarChart = lazy(() =>
  import("@/components/dashboard/AttainmentBarChart").then((m) => ({
    default: m.AttainmentBarChart,
  })),
);

export function DashboardChartsRoute() {
  const { filters } = useFilters();
  const dash = useDashboard(filters);

  if (dash.isLoading) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        Loading charts…
      </div>
    );
  }
  if (!dash.data || dash.data.rows.length === 0) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        No data to chart.
      </div>
    );
  }

  return (
    <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <Suspense
        fallback={
          <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
            Loading bookings chart…
          </div>
        }
      >
        <BookingsBarChart rows={dash.data.rows} />
      </Suspense>
      <Suspense
        fallback={
          <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
            Loading attainment chart…
          </div>
        }
      >
        <AttainmentBarChart rows={dash.data.rows} />
      </Suspense>
    </section>
  );
}
