import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown, Search } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";

interface Props<TRow> {
  data: TRow[];
  columns: ColumnDef<TRow, unknown>[];
  /** Empty-state label. */
  emptyMessage?: string;
  /** Show a single global-search box across all visible cells. */
  enableGlobalSearch?: boolean;
  /** Show per-column text-filter inputs in a row below the header. */
  enableColumnFilters?: boolean;
  /** Page-size options. Set [] to disable pagination. */
  pageSizes?: number[];
  /** Initial page size; first entry of pageSizes by default. */
  initialPageSize?: number;
  /** Pin first column on horizontal scroll. */
  stickyFirstColumn?: boolean;
}

const DEFAULT_PAGE_SIZES = [10, 25, 50, 100];

export function DataTable<TRow>({
  data,
  columns,
  emptyMessage = "No rows.",
  enableGlobalSearch = true,
  enableColumnFilters = false,
  pageSizes = DEFAULT_PAGE_SIZES,
  initialPageSize,
  stickyFirstColumn = true,
}: Props<TRow>) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const paginationEnabled = pageSizes.length > 0;

  const table = useReactTable<TRow>({
    data,
    columns,
    state: { globalFilter, sorting, columnFilters },
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: paginationEnabled ? getPaginationRowModel() : undefined,
    initialState: paginationEnabled
      ? { pagination: { pageIndex: 0, pageSize: initialPageSize ?? pageSizes[0] } }
      : undefined,
  });

  const colCount = table.getVisibleLeafColumns().length;
  const totalRows = table.getFilteredRowModel().rows.length;

  return (
    <div className="space-y-2">
      {enableGlobalSearch && (
        <div className="flex items-center gap-2 text-sm">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder="Search rows…"
              className="h-8 w-56 rounded-md border border-border bg-background pl-7 pr-2 text-sm"
            />
          </div>
          <span className="text-xs text-muted-foreground">
            {totalRows} row{totalRows === 1 ? "" : "s"}
          </span>
        </div>
      )}

      <div className="max-w-full overflow-x-auto overflow-y-visible rounded-md border border-border">
        <table className="w-max min-w-full border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-20 bg-muted/70 backdrop-blur">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header, idx) => {
                  const canSort = header.column.getCanSort();
                  const sortDir = header.column.getIsSorted();
                  const sticky = stickyFirstColumn && idx === 0;
                  return (
                    <th
                      key={header.id}
                      colSpan={header.colSpan}
                      className={cn(
                        "whitespace-nowrap border-b border-border px-2 py-2 text-left text-xs font-medium text-muted-foreground",
                        sticky && "sticky left-0 z-30 bg-muted/70",
                        canSort && "cursor-pointer select-none",
                      )}
                      onClick={
                        canSort
                          ? header.column.getToggleSortingHandler()
                          : undefined
                      }
                    >
                      {header.isPlaceholder ? null : (
                        <span className="inline-flex items-center gap-1">
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          {canSort &&
                            (sortDir === "asc" ? (
                              <ArrowUp className="h-3 w-3" />
                            ) : sortDir === "desc" ? (
                              <ArrowDown className="h-3 w-3" />
                            ) : (
                              <ChevronsUpDown className="h-3 w-3 text-muted-foreground/40" />
                            ))}
                        </span>
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
            {enableColumnFilters && (
              <tr>
                {table.getVisibleLeafColumns().map((col, idx) => {
                  const sticky = stickyFirstColumn && idx === 0;
                  return (
                    <th
                      key={`${col.id}-filter`}
                      className={cn(
                        "border-b border-border px-2 py-1",
                        sticky && "sticky left-0 z-30 bg-muted/70",
                      )}
                    >
                      {col.getCanFilter() ? (
                        <input
                          value={(col.getFilterValue() as string) ?? ""}
                          onChange={(e) => col.setFilterValue(e.target.value)}
                          placeholder="filter…"
                          className="h-6 w-full rounded border border-border bg-background px-1 text-xs"
                        />
                      ) : null}
                    </th>
                  );
                })}
              </tr>
            )}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 && (
              <tr>
                <td
                  colSpan={colCount}
                  className="px-4 py-6 text-center text-sm text-muted-foreground"
                >
                  {emptyMessage}
                </td>
              </tr>
            )}
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-border">
                {row.getVisibleCells().map((cell, idx) => {
                  const sticky = stickyFirstColumn && idx === 0;
                  return (
                    <td
                      key={cell.id}
                      className={cn(
                        "whitespace-nowrap px-2 py-1.5 text-sm",
                        sticky && "sticky left-0 z-10 bg-background",
                      )}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {paginationEnabled && totalRows > 0 && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span>Rows per page</span>
            <select
              value={table.getState().pagination.pageSize}
              onChange={(e) => table.setPageSize(Number(e.target.value))}
              className="h-7 rounded-md border border-border bg-background px-1"
            >
              {pageSizes.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span>
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount() || 1}
            </span>
            <button
              type="button"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="h-7 rounded-md border border-border bg-background px-2 disabled:opacity-40"
            >
              Prev
            </button>
            <button
              type="button"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="h-7 rounded-md border border-border bg-background px-2 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
