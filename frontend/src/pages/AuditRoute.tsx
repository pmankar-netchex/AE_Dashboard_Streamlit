import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { type AuditPage, fetchAudit } from "@/api/audit";
import { formatInTz, useTz } from "@/lib/datetime";
import { cn } from "@/lib/cn";

const ENTITY_FILTERS = ["", "user", "soql", "salesforce", "schedule"];
const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-100 text-green-900",
  update: "bg-blue-100 text-blue-900",
  delete: "bg-red-100 text-red-900",
  refresh: "bg-purple-100 text-purple-900",
  "refresh-failed": "bg-amber-100 text-amber-900",
  run: "bg-slate-100 text-slate-900",
};

export function AuditRoute() {
  const tz = useTz();
  const [entity, setEntity] = useState<string>("");
  const [cursor, setCursor] = useState<string | null>(null);
  const { data, isLoading } = useQuery<AuditPage>({
    queryKey: ["audit", entity, cursor],
    queryFn: () => fetchAudit({ entity: entity || null, cursor }),
  });

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Activity / Audit Log</h1>
        <p className="text-sm text-muted-foreground">
          Read-only timeline of governance events.
        </p>
      </header>

      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">Entity</span>
        <div className="inline-flex overflow-hidden rounded-md border border-border">
          {ENTITY_FILTERS.map((e) => (
            <button
              key={e || "all"}
              type="button"
              onClick={() => {
                setEntity(e);
                setCursor(null);
              }}
              className={cn(
                "px-2.5 py-1 text-xs capitalize",
                entity === e
                  ? "bg-primary text-primary-foreground"
                  : "bg-background hover:bg-accent",
              )}
            >
              {e || "All"}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-md border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-xs">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Time
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Actor
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Entity
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Action
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Target
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Details
              </th>
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
            {data?.events.length === 0 && !isLoading && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                  No events yet.
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

      {data?.next_cursor && (
        <button
          type="button"
          onClick={() => setCursor(data.next_cursor)}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent"
        >
          Next page
        </button>
      )}
    </div>
  );
}
