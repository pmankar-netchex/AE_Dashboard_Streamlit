import type { AERow, ColumnMeta } from "@/types/dashboard";
import { rdylgnFor } from "@/lib/heatmap";
import { fmt } from "@/lib/formatters";
import { LOWER_IS_BETTER } from "@/lib/columns";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface Props {
  rows: AERow[];
  columns: ColumnMeta[];
}

export function PerformanceHeatmap({ rows, columns }: Props) {
  const numericCols = columns.filter((c) => !c.blocked && !c.computed);
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
          Per-column normalized; red→yellow→green. Hover a cell for the AE, column, and value.
        </p>
      </header>
      <div className="overflow-x-auto">
        <div
          className="grid"
          style={{
            gridTemplateColumns: `200px repeat(${numericCols.length}, minmax(40px, 1fr))`,
          }}
        >
          <div className="sticky left-0 z-10 bg-background px-2 py-2 text-xs font-medium text-muted-foreground">
            AE
          </div>
          {numericCols.map((c) => (
            <InfoTooltip
              key={c.col_id}
              title={c.display_name}
              description={c.description || c.aggregation || c.col_id}
              side="bottom"
            >
              <div className="cursor-help truncate px-1 py-2 text-center text-[10px] font-medium text-muted-foreground">
                {abbreviate(c.display_name)}
              </div>
            </InfoTooltip>
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
        className="sticky left-0 z-10 truncate bg-background px-2 py-2 text-xs"
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
          <InfoTooltip
            key={c.col_id}
            title={`${row.ae_name} — ${c.display_name}`}
            description={`${fmt(v, c.format)}${c.description ? "\n" + c.description : ""}`}
            side="top"
          >
            <div
              className="h-7 cursor-help border border-transparent transition-[border-color,box-shadow] hover:border-foreground/70 hover:shadow-[0_0_0_1px_rgba(0,0,0,0.05)]"
              style={{ backgroundColor: rdylgnFor(norm) }}
              aria-label={`${row.ae_name} — ${c.display_name}: ${fmt(v, c.format)}`}
            />
          </InfoTooltip>
        );
      })}
    </>
  );
}

/**
 * Compact header label for the heatmap grid. Tries to keep things distinct
 * (uses 2-3 chars from each significant word) without leaning on the cryptic
 * col_id suffix. Falls back to the trimmed col_id when display_name is empty.
 */
function abbreviate(displayName: string): string {
  if (!displayName) return "—";
  const cleaned = displayName.replace(/\([^)]*\)/g, "").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 6);
  return parts
    .slice(0, 3)
    .map((p, i) => (i === 0 ? p.slice(0, 3) : p.slice(0, 2)))
    .join(" ");
}
