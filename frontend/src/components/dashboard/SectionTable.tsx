import {
  type ColumnDef,
  createColumnHelper,
} from "@tanstack/react-table";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
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
  defaultOpen?: boolean;
}

const helper = createColumnHelper<AERow>();

export function SectionTable({ section, columns, rows, defaultOpen }: Props) {
  const [open, setOpen] = useState(!!defaultOpen);
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
        enableColumnFilter: true,
      }),
      helper.accessor("ae_manager", {
        id: "manager",
        header: "AE Manager",
        cell: (c) => <span className="text-muted-foreground">{c.getValue() as string}</span>,
        enableColumnFilter: true,
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
        <div className="border-t border-border p-3">
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
        </div>
      )}
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
