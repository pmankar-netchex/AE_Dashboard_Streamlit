import {
  type ColumnDef,
  createColumnHelper,
} from "@tanstack/react-table";
import { useMemo } from "react";
import type { AllSourceSummaryRow, AllSourceSummarySpec } from "@/types/dashboard";
import { useFilters } from "@/hooks/useFilters";
import { fmt } from "@/lib/formatters";
import { lightHeatmapColor, normalizeColumn } from "@/lib/heatmap";
import { DataTable } from "@/components/tables/DataTable";
import { cn } from "@/lib/cn";

interface Props {
  rows: AllSourceSummaryRow[];
  sources: AllSourceSummarySpec[];
}

const helper = createColumnHelper<AllSourceSummaryRow>();

function HeatedNumber({
  value,
  norm,
}: {
  value: number | null;
  norm: number | null;
}) {
  return (
    <span
      className="block w-full rounded px-1.5 py-0.5 text-right tabular-nums"
      style={{ backgroundColor: lightHeatmapColor(norm) }}
    >
      {fmt(value, "currency")}
    </span>
  );
}

export function AllSourceSummary({ rows, sources }: Props) {
  const { set } = useFilters();

  const norms = useMemo(() => {
    const tp = normalizeColumn(rows.map((r) => r.total_pipeline));
    const tb = normalizeColumn(rows.map((r) => r.total_bookings));
    const perSource = sources.map((_, i) => ({
      p: normalizeColumn(rows.map((r) => r.sources[i]?.pipeline ?? null)),
      b: normalizeColumn(rows.map((r) => r.sources[i]?.bookings ?? null)),
    }));
    return { tp, tb, perSource };
  }, [rows, sources]);

  const idxByRow = useMemo(() => {
    const m = new Map<string, number>();
    rows.forEach((r, i) => m.set(r.ae_id || r.ae_name, i));
    return m;
  }, [rows]);

  const columns = useMemo<ColumnDef<AllSourceSummaryRow, unknown>[]>(() => {
    const sourceGroups = sources.map((s, i) =>
      helper.group({
        id: `src-${s.label}`,
        header: () => <span className="text-foreground">{s.label}</span>,
        columns: [
          helper.accessor((r) => r.sources[i]?.pipeline ?? null, {
            id: `${s.label}-p`,
            header: "Pipeline",
            cell: (c) => {
              const rowIdx = idxByRow.get(c.row.original.ae_id || c.row.original.ae_name) ?? 0;
              return (
                <HeatedNumber value={c.getValue() as number | null} norm={norms.perSource[i].p[rowIdx]} />
              );
            },
            sortingFn: numericSort,
          }),
          helper.accessor((r) => r.sources[i]?.bookings ?? null, {
            id: `${s.label}-b`,
            header: "Bookings",
            cell: (c) => {
              const rowIdx = idxByRow.get(c.row.original.ae_id || c.row.original.ae_name) ?? 0;
              return (
                <HeatedNumber value={c.getValue() as number | null} norm={norms.perSource[i].b[rowIdx]} />
              );
            },
            sortingFn: numericSort,
          }),
        ],
      }),
    );

    return [
      helper.accessor("ae_name", {
        id: "ae",
        header: "AE",
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
            title={c.row.original.ae_id ? "Open AE drill-down" : "No AE id"}
          >
            {c.getValue() as string}
          </button>
        ),
        enableColumnFilter: true,
      }),
      helper.accessor("ae_manager", {
        id: "manager",
        header: "Manager",
        cell: (c) => <span className="text-muted-foreground">{c.getValue() as string}</span>,
        enableColumnFilter: true,
      }),
      helper.group({
        id: "totals",
        header: () => <span className="text-foreground">Totals (Period)</span>,
        columns: [
          helper.accessor("total_pipeline", {
            id: "total_pipeline",
            header: "Pipeline",
            cell: (c) => {
              const rowIdx = idxByRow.get(c.row.original.ae_id || c.row.original.ae_name) ?? 0;
              return (
                <HeatedNumber value={c.getValue() as number | null} norm={norms.tp[rowIdx]} />
              );
            },
            sortingFn: numericSort,
          }),
          helper.accessor("total_bookings", {
            id: "total_bookings",
            header: "Bookings",
            cell: (c) => {
              const rowIdx = idxByRow.get(c.row.original.ae_id || c.row.original.ae_name) ?? 0;
              return (
                <HeatedNumber value={c.getValue() as number | null} norm={norms.tb[rowIdx]} />
              );
            },
            sortingFn: numericSort,
          }),
        ],
      }),
      ...sourceGroups,
    ];
  }, [sources, norms, idxByRow, set]);

  return (
    <section>
      <header className="mb-2 flex items-center justify-between">
        <h2 className="text-base font-semibold">All Source Summary</h2>
        <p className="text-xs text-muted-foreground">
          Totals first, then split-credited Pipeline $ and Bookings $ by source.
        </p>
      </header>
      <DataTable
        data={rows}
        columns={columns}
        emptyMessage="No AEs match the current filters."
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
