import * as Tooltip from "@radix-ui/react-tooltip";
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
      <header className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium">Performance Heatmap</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Per-column normalized. Hover a cell for the AE, column, and value.
          </p>
        </div>
        <Legend />
      </header>

      <div className="overflow-x-auto">
        <div
          className="grid gap-px bg-border"
          style={{
            gridTemplateColumns: `200px repeat(${numericCols.length}, minmax(56px, 1fr))`,
          }}
        >
          {/* Header row */}
          <div className="sticky left-0 z-10 bg-background px-2 py-2 text-xs font-medium text-muted-foreground">
            AE
          </div>
          {numericCols.map((c) => (
            <Tooltip.Root key={`h-${c.col_id}`}>
              <Tooltip.Trigger asChild>
                <div className="cursor-help truncate bg-background px-1 py-2 text-center text-[10px] font-medium text-muted-foreground">
                  {abbreviate(c)}
                </div>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content
                  side="bottom"
                  sideOffset={4}
                  className="z-50 max-w-xs rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
                >
                  <div className="font-medium text-foreground">{c.display_name}</div>
                  {(c.description || c.aggregation) && (
                    <div className="mt-1 leading-snug text-muted-foreground">
                      {c.description || c.aggregation}
                    </div>
                  )}
                  <Tooltip.Arrow className="fill-background" />
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          ))}

          {/* Data rows */}
          {rows.map((r) =>
            renderRow({ row: r, cols: numericCols, maxByCol }),
          )}
        </div>
      </div>
    </section>
  );
}

function renderRow({
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
        key={`r-${row.ae_id}`}
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
          <Tooltip.Root key={`${row.ae_id}-${c.col_id}`}>
            <Tooltip.Trigger asChild>
              <div
                className="h-8 cursor-help transition-[box-shadow] hover:shadow-[inset_0_0_0_2px_rgba(0,0,0,0.65)]"
                style={{ backgroundColor: rdylgnFor(norm) }}
                aria-label={`${row.ae_name} — ${c.display_name}: ${fmt(v, c.format)}`}
              />
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                sideOffset={4}
                className="z-50 max-w-xs rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
              >
                <div className="font-medium text-foreground">
                  {row.ae_name} — {c.display_name}
                </div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  {fmt(v, c.format)}
                </div>
                {c.description && (
                  <div className="mt-1 leading-snug text-muted-foreground">
                    {c.description}
                  </div>
                )}
                <Tooltip.Arrow className="fill-background" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        );
      })}
    </>
  );
}

/** Render a tiny gradient bar legend on the right of the section header. */
function Legend() {
  const stops = [0, 0.25, 0.5, 0.75, 1];
  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
      <span>Worse</span>
      <div className="flex h-3 w-32 overflow-hidden rounded border border-border">
        {stops.map((s) => (
          <div
            key={s}
            className="h-full flex-1"
            style={{ backgroundColor: rdylgnFor(s) }}
          />
        ))}
      </div>
      <span>Better</span>
    </div>
  );
}

/**
 * Compact, unique header label for the heatmap grid.
 *
 * Preserves a period marker (YTD / MTD / "This Month" / "Next Month") so
 * "Quota (YTD)" and "Quota (MTD)" don't both collapse to "Quota".
 */
function abbreviate(c: ColumnMeta): string {
  const display = c.display_name || c.col_id;
  const periodMatch = display.match(/\(([^)]+)\)/);
  const cleaned = display.replace(/\([^)]*\)/g, "").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  const base =
    parts.length === 1
      ? parts[0].slice(0, 6)
      : parts
          .slice(0, 2)
          .map((p, i) => (i === 0 ? p.slice(0, 4) : p.slice(0, 3)))
          .join(" ");
  if (periodMatch) {
    return `${base} ${shortPeriod(periodMatch[1])}`;
  }
  return base;
}

function shortPeriod(p: string): string {
  const lower = p.toLowerCase();
  if (lower === "ytd" || lower === "mtd" || lower === "qtd") return lower.toUpperCase();
  if (lower.includes("this month")) return "TM";
  if (lower.includes("next month")) return "NM";
  if (lower.includes("last month")) return "LM";
  return p.slice(0, 3);
}
