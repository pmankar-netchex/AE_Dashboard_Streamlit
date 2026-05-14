import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { AERow, ColumnMeta } from "@/types/dashboard";
import { LOWER_IS_BETTER } from "@/lib/columns";
import { normalizeColumn } from "@/lib/heatmap";
import { AENameCell } from "@/components/tables/AENameCell";
import { HeatmapCell } from "@/components/tables/HeatmapCell";
import { cn } from "@/lib/cn";

interface Props {
  section: { key: string; display_name: string };
  columns: ColumnMeta[];
  rows: AERow[];
  defaultOpen?: boolean;
}

export function SectionTable({ section, columns, rows, defaultOpen }: Props) {
  const [open, setOpen] = useState(!!defaultOpen);
  const numericCols = columns.filter((c) => !c.blocked);

  const norms: Record<string, (number | null)[]> = {};
  for (const col of numericCols) {
    if (col.computed) continue;
    norms[col.col_id] = normalizeColumn(
      rows.map((r) => r.values[col.col_id]),
      LOWER_IS_BETTER.has(col.col_id),
    );
  }

  return (
    <section className="rounded-lg border border-border">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm font-medium hover:bg-accent"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          {section.display_name}
        </span>
        <span className="text-xs text-muted-foreground">
          {numericCols.length} columns
        </span>
      </button>
      {open && (
        <div className="overflow-auto border-t border-border">
          <table className="min-w-full border-separate border-spacing-0">
            <thead className="bg-muted/30">
              <tr>
                <th className="sticky left-0 z-10 bg-muted/30 px-2 py-2 text-left text-xs font-medium text-muted-foreground">
                  AE Name
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium text-muted-foreground">
                  AE Manager
                </th>
                {numericCols.map((c) => (
                  <th
                    key={c.col_id}
                    className={cn(
                      "whitespace-nowrap px-2 py-2 text-right text-xs font-medium",
                      c.blocked ? "text-muted-foreground/60" : "text-muted-foreground",
                    )}
                    title={c.description}
                  >
                    {c.display_name}
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
                  {numericCols.map((c) => {
                    if (c.blocked) {
                      return (
                        <td
                          key={c.col_id}
                          className="px-2 py-1.5 text-right text-xs italic text-muted-foreground/60"
                        >
                          Pending
                        </td>
                      );
                    }
                    return (
                      <HeatmapCell
                        key={c.col_id}
                        value={row.values[c.col_id]}
                        norm={norms[c.col_id]?.[rowIdx] ?? null}
                        format={c.format}
                      />
                    );
                  })}
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td
                    colSpan={2 + numericCols.length}
                    className="px-4 py-6 text-center text-sm text-muted-foreground"
                  >
                    No data.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
