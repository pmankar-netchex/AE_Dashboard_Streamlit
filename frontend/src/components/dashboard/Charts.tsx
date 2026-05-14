import { lazy, Suspense } from "react";
import type { AERow, ColumnMeta } from "@/types/dashboard";

const BookingsBarChart = lazy(() =>
  import("./BookingsBarChart").then((m) => ({ default: m.BookingsBarChart })),
);
const AttainmentBarChart = lazy(() =>
  import("./AttainmentBarChart").then((m) => ({ default: m.AttainmentBarChart })),
);
const PerformanceHeatmap = lazy(() =>
  import("./PerformanceHeatmap").then((m) => ({ default: m.PerformanceHeatmap })),
);

function Skeleton({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
      Loading {label}…
    </div>
  );
}

interface Props {
  rows: AERow[];
  columns: ColumnMeta[];
}

export function DashboardCharts({ rows, columns }: Props) {
  return (
    <>
      <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Suspense fallback={<Skeleton label="bookings chart" />}>
          <BookingsBarChart rows={rows} />
        </Suspense>
        <Suspense fallback={<Skeleton label="attainment chart" />}>
          <AttainmentBarChart rows={rows} />
        </Suspense>
      </section>
      <Suspense fallback={<Skeleton label="performance heatmap" />}>
        <PerformanceHeatmap rows={rows} columns={columns} />
      </Suspense>
    </>
  );
}
