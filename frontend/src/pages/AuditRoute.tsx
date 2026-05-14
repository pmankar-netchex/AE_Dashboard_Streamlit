import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { type AuditPage, fetchAudit } from "@/api/audit";
import { formatInTz, useTz } from "@/lib/datetime";
import { cn } from "@/lib/cn";

const ENTITY_FILTERS = ["", "user", "soql", "salesforce", "schedule"] as const;
const PAGE_SIZES = [25, 50, 100, 200] as const;

const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-100 text-green-900",
  update: "bg-blue-100 text-blue-900",
  delete: "bg-red-100 text-red-900",
  refresh: "bg-purple-100 text-purple-900",
  "refresh-failed": "bg-amber-100 text-amber-900",
  run: "bg-slate-100 text-slate-900",
  "send-now": "bg-slate-100 text-slate-900",
  "send-once": "bg-slate-100 text-slate-900",
  "send-once-failed": "bg-amber-100 text-amber-900",
};

export function AuditRoute() {
  const tz = useTz();
  const [entity, setEntity] = useState<string>("");
  const [pageSize, setPageSize] = useState<number>(50);
  // Stack of cursors that take us to each page. cursorStack[i] is the cursor
  // to fetch page i (0 = first page → null cursor).
  const [cursorStack, setCursorStack] = useState<(string | null)[]>([null]);
  const cursor = cursorStack[cursorStack.length - 1] ?? null;
  const pageNum = cursorStack.length;

  const { data, isLoading, isFetching } = useQuery<AuditPage>({
    queryKey: ["audit", entity, pageSize, cursor],
    queryFn: () =>
      fetchAudit({ entity: entity || null, cursor, page_size: pageSize }),
    placeholderData: (prev) => prev,
  });

  const goPrev = (): void => {
    if (cursorStack.length > 1) {
      setCursorStack(cursorStack.slice(0, -1));
    }
  };
  const goNext = (): void => {
    if (data?.next_cursor) {
      setCursorStack([...cursorStack, data.next_cursor]);
    }
  };

  const reset = (next?: Partial<{ entity: string; pageSize: number }>): void => {
    if (next?.entity !== undefined) setEntity(next.entity);
    if (next?.pageSize !== undefined) setPageSize(next.pageSize);
    setCursorStack([null]);
  };

  const rowCount = data?.events.length ?? 0;
  const hasNext = !!data?.next_cursor;
  const hasPrev = cursorStack.length > 1;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Activity / Audit Log</h1>
        <p className="text-sm text-muted-foreground">
          Read-only timeline of governance events. Newest first.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Entity</span>
          <div className="inline-flex overflow-hidden rounded-md border border-border">
            {ENTITY_FILTERS.map((e) => (
              <button
                key={e || "all"}
                type="button"
                onClick={() => reset({ entity: e })}
                className={cn(
                  "px-2.5 py-1 text-xs capitalize",
                  entity === e
                    ? "bg-accent font-medium text-foreground"
                    : "bg-background text-muted-foreground hover:bg-accent hover:text-foreground",
                )}
              >
                {e || "All"}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Page size</span>
          <select
            value={pageSize}
            onChange={(e) => reset({ pageSize: Number(e.target.value) })}
            className="h-7 rounded-md border border-border bg-background px-1 text-xs"
          >
            {PAGE_SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-hidden rounded-md border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-xs">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Time</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Actor</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Entity</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Action</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Target</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Details</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && rowCount === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                  No events to show.
                </td>
              </tr>
            )}
            {data?.events.map((ev, i) => (
              <tr key={`${ev.timestamp}-${i}`} className="border-t border-border">
                <td className="whitespace-nowrap px-3 py-2 text-xs text-muted-foreground">
                  {formatInTz(ev.timestamp, tz)}
                </td>
                <td className="px-3 py-2 text-xs">{ev.actor}</td>
                <td className="px-3 py-2 text-xs capitalize">{ev.entity}</td>
                <td className="px-3 py-2">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[11px]",
                      ACTION_COLORS[ev.action] ?? "bg-muted text-muted-foreground",
                    )}
                  >
                    {ev.action}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{ev.target || "—"}</td>
                <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">
                  {Object.keys(ev.details).length > 0
                    ? JSON.stringify(ev.details)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {isFetching && !isLoading ? "Loading…" : `Page ${pageNum} • ${rowCount} row${rowCount === 1 ? "" : "s"}`}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={goPrev}
            disabled={!hasPrev || isFetching}
            className="rounded-md border border-border bg-background px-2 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={!hasNext || isFetching}
            className="rounded-md border border-border bg-background px-2 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
