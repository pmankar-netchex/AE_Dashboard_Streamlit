import type { KpiValue } from "@/types/dashboard";
import { KpiCard } from "./KpiCard";

interface Props {
  row1: KpiValue[];
  row2: KpiValue[];
}

export function KpiRow({ row1, row2 }: Props) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-medium text-muted-foreground">
        Key Performance Indicators
      </h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {row1.map((k) => (
          <KpiCard key={`r1-${k.col_id}`} kpi={k} />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        {row2.map((k) => (
          <KpiCard key={`r2-${k.col_id}`} kpi={k} />
        ))}
      </div>
    </section>
  );
}
