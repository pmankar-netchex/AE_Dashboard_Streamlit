import { useMemo } from "react";
import type { AllSourceSummaryRow, AllSourceSummarySpec } from "@/types/dashboard";
import { normalizeColumn } from "@/lib/heatmap";
import { AENameCell } from "@/components/tables/AENameCell";
import { HeatmapCell } from "@/components/tables/HeatmapCell";

interface Props {
  rows: AllSourceSummaryRow[];
  sources: AllSourceSummarySpec[];
}

interface NumericCol {
  key: string;
  label: string;
  getValue: (row: AllSourceSummaryRow) => number | null;
}

export function AllSourceSummary({ rows, sources }: Props) {
  const numericCols: NumericCol[] = useMemo(() => {
    const cols: NumericCol[] = [
      {
        key: "total_pipeline",
        label: "Total Pipeline (Period)",
        getValue: (r) => r.total_pipeline,
      },
      {
        key: "total_bookings",
        label: "Total Bookings (Period)",
        getValue: (r) => r.total_bookings,
      },
    ];
    sources.forEach((s, idx) => {
      cols.push({
        key: `${s.label}-p`,
        label: `${s.label} Pipeline`,
        getValue: (r) => r.sources[idx]?.pipeline ?? null,
      });
      cols.push({
        key: `${s.label}-b`,
        label: `${s.label} Bookings`,
        getValue: (r) => r.sources[idx]?.bookings ?? null,
      });
    });
    return cols;
  }, [sources]);

  const norms = useMemo(() => {
    const out: Record<string, (number | null)[]> = {};
    for (const col of numericCols) {
      out[col.key] = normalizeColumn(rows.map((r) => col.getValue(r)));
    }
    return out;
  }, [numericCols, rows]);

  return (
    <section>
      <header className="mb-2 flex items-center justify-between">
        <h2 className="text-base font-semibold">All Source Summary</h2>
        <p className="text-xs text-muted-foreground">
          Totals first, then split-credited Pipeline $ and Bookings $ by source.
        </p>
      </header>
      <div className="overflow-auto rounded-lg border border-border">
        <table className="min-w-full border-separate border-spacing-0">
          <thead className="bg-muted/50">
            <tr>
              <th className="sticky left-0 z-10 bg-muted/50 px-2 py-2 text-left text-xs font-medium text-muted-foreground">
                AE
              </th>
              <th className="px-2 py-2 text-left text-xs font-medium text-muted-foreground">
                Manager
              </th>
              {numericCols.map((c) => (
                <th
                  key={c.key}
                  className="whitespace-nowrap px-2 py-2 text-right text-xs font-medium text-muted-foreground"
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <tr key={row.ae_id} className="border-t border-border">
                <AENameCell aeId={row.ae_id} name={row.ae_name} />
                <td className="px-2 py-1.5 text-sm text-muted-foreground">
                  {row.ae_manager}
                </td>
                {numericCols.map((col) => (
                  <HeatmapCell
                    key={col.key}
                    value={col.getValue(row)}
                    norm={norms[col.key]?.[rowIdx] ?? null}
                    format="currency"
                  />
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={2 + numericCols.length}
                  className="px-4 py-6 text-center text-sm text-muted-foreground"
                >
                  No AEs match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
