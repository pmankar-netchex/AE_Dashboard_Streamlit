import type { AERow, ColumnMeta } from "@/types/dashboard";
import { rdylgnFor } from "@/lib/heatmap";
import { fmt } from "@/lib/formatters";
import { LOWER_IS_BETTER } from "@/lib/columns";

interface Props {
  rows: AERow[];
  columns: ColumnMeta[];
}

export function PerformanceHeatmap({ rows, columns }: Props) {
  const numericCols = columns.filter((c) => !c.blocked && !c.computed);
  // Normalize per column over the max value (mirrors dashboard_ui display_heatmap).
  const maxByCol: Record<string, number> = {};
  for (const c of numericCols) {
    let max = 0;
    for (const r of rows) {
      const v = r.values[c.col_id];
      if (v != null && Number.isFinite(v)) max = Math.max(max, Math.abs(v as number));
    }
    maxByCol[c.col_id] = max;
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        No data to render heatmap.
      </div>
    );
  }

  return (
    <section className="rounded-lg border border-border p-4">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium">Performance Heatmap</h3>
        <p className="text-xs text-muted-foreground">
          Per-column normalized; red→yellow→green.
        </p>
      </header>
      <div className="overflow-auto">
        <div
          className="grid"
          style={{
            gridTemplateColumns: `200px repeat(${numericCols.length}, minmax(64px, 1fr))`,
          }}
        >
          <div className="sticky left-0 z-10 bg-background px-2 py-1.5 text-xs font-medium text-muted-foreground">
            AE
          </div>
          {numericCols.map((c) => (
            <div
              key={c.col_id}
              className="truncate px-1 py-1.5 text-center text-[10px] font-medium text-muted-foreground"
              title={c.display_name}
            >
              {c.col_id.replace(/^S\d+-COL-/, "")}
            </div>
          ))}
          {rows.map((r) => (
            <FragmentRow key={r.ae_id} row={r} cols={numericCols} maxByCol={maxByCol} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FragmentRow({
  row,
  cols,
  maxByCol,
}: {
  row: AERow;
  cols: ColumnMeta[];
  maxByCol: Record<string, number>;
}) {
  return (
    <>
      <div
        className="sticky left-0 z-10 truncate bg-background px-2 py-1.5 text-xs"
        title={row.ae_name}
      >
        {row.ae_name}
      </div>
      {cols.map((c) => {
        const v = row.values[c.col_id];
        const max = maxByCol[c.col_id] || 1;
        let norm: number | null = null;
        if (v != null && Number.isFinite(v)) {
          const raw = Math.min(1, Math.max(0, Math.abs(v as number) / max));
          norm = LOWER_IS_BETTER.has(c.col_id) ? 1 - raw : raw;
        }
        return (
          <div
            key={c.col_id}
            className="px-1 py-1.5 text-center text-[10px] tabular-nums text-white"
            style={{
              backgroundColor: rdylgnFor(norm),
              color: norm == null || norm < 0.6 ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.85)",
            }}
            title={`${row.ae_name} • ${c.display_name} = ${fmt(v, c.format)}`}
          >
            {fmt(v, c.format)}
          </div>
        );
      })}
    </>
  );
}
