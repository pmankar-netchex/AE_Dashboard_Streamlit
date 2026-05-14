import {
  type ColumnDef,
  createColumnHelper,
} from "@tanstack/react-table";
import { useMemo } from "react";
import type { AERow, ColumnMeta } from "@/types/dashboard";
import { DataTable } from "@/components/tables/DataTable";
import { useFilters } from "@/hooks/useFilters";
import { LOWER_IS_BETTER } from "@/lib/columns";
import { fmt } from "@/lib/formatters";
import { lightHeatmapColor, normalizeColumn } from "@/lib/heatmap";
import { cn } from "@/lib/cn";

interface Props {
  section: { key: string; display_name: string };
  columns: ColumnMeta[];
  rows: AERow[];
  /** Show a section title above the table. Set false to render bare. */
  showHeader?: boolean;
}

const helper = createColumnHelper<AERow>();

export function SectionTable({ section, columns, rows, showHeader = true }: Props) {
  const { set } = useFilters();

  const numericCols = columns.filter((c) => !c.blocked);

  const norms = useMemo(() => {
    const out: Record<string, (number | null)[]> = {};
    for (const c of numericCols) {
      if (c.computed) continue;
      out[c.col_id] = normalizeColumn(
        rows.map((r) => r.values[c.col_id]),
        LOWER_IS_BETTER.has(c.col_id),
      );
    }
    return out;
  }, [numericCols, rows]);

  const idxByRow = useMemo(() => {
    const m = new Map<string, number>();
    rows.forEach((r, i) => m.set(r.ae_id || r.ae_name, i));
    return m;
  }, [rows]);

  const tableColumns = useMemo<ColumnDef<AERow, unknown>[]>(() => {
    const defs: ColumnDef<AERow, unknown>[] = [
      helper.accessor("ae_name", {
        id: "ae",
        header: "AE Name",
        cell: (c) => (
          <button
            type="button"
            onClick={() => set({ aeDrillId: c.row.original.ae_id })}
            className={cn(
              "text-left font-medium",
              c.row.original.ae_id
                ? "hover:underline"
                : "text-muted-foreground",
            )}
            disabled={!c.row.original.ae_id}
          >
            {c.getValue() as string}
          </button>
        ),
      }),
      helper.accessor("ae_manager", {
        id: "manager",
        header: "AE Manager",
        cell: (c) => <span className="text-muted-foreground">{c.getValue() as string}</span>,
      }),
    ];

    for (const col of numericCols) {
      defs.push(
        helper.accessor((r) => r.values[col.col_id] ?? null, {
          id: col.col_id,
          header: () => (
            <span title={col.description}>{col.display_name}</span>
          ),
          cell: (c) => {
            if (col.blocked) {
              return <span className="text-xs italic text-muted-foreground/60">Pending</span>;
            }
            const rowIdx = idxByRow.get(c.row.original.ae_id || c.row.original.ae_name) ?? 0;
            const norm = norms[col.col_id]?.[rowIdx] ?? null;
            return (
              <span
                className="block w-full rounded px-1.5 py-0.5 text-right tabular-nums"
                style={{ backgroundColor: lightHeatmapColor(norm) }}
              >
                {fmt(c.getValue() as number | null, col.format)}
              </span>
            );
          },
          sortingFn: numericSort,
        }),
      );
    }
    return defs;
  }, [numericCols, norms, idxByRow, set]);

  return (
    <section className="space-y-2">
      {showHeader && (
        <header className="flex items-center justify-between">
          <h2 className="text-base font-semibold">{section.display_name}</h2>
          <p className="text-xs text-muted-foreground">{numericCols.length} columns</p>
        </header>
      )}
      <DataTable
        data={rows}
        columns={tableColumns}
        emptyMessage="No data."
        enableGlobalSearch
        enableColumnFilters={false}
        pageSizes={[10, 25, 50, 100]}
        initialPageSize={25}
        stickyFirstColumn
      />
    </section>
  );
}

function numericSort(rowA: { getValue: (id: string) => unknown }, rowB: { getValue: (id: string) => unknown }, colId: string) {
  const a = rowA.getValue(colId) as number | null;
  const b = rowB.getValue(colId) as number | null;
  if (a === null) return b === null ? 0 : 1;
  if (b === null) return -1;
  return a - b;
}
