import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Send, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  type Schedule,
  deleteSchedule,
  listSchedules,
  sendNow,
  updateSchedule,
} from "@/api/schedules";
import { ReadOnlyGate, useReadOnly } from "@/components/auth/ReadOnlyGate";
import { ScheduleForm } from "@/components/schedules/ScheduleForm";
import { cn } from "@/lib/cn";

export function SchedulesRoute() {
  return (
    <ReadOnlyGate>
      <SchedulesInner />
    </ReadOnlyGate>
  );
}

function SchedulesInner() {
  const readOnly = useReadOnly();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Schedule | null>(null);
  const [creating, setCreating] = useState(false);
  const { data, isLoading } = useQuery<Schedule[]>({
    queryKey: ["schedules"],
    queryFn: listSchedules,
  });

  const invalidate = (): void => {
    void qc.invalidateQueries({ queryKey: ["schedules"] });
  };

  const toggleActive = useMutation({
    mutationFn: (s: Schedule) =>
      updateSchedule(s.id, { is_active: !s.is_active }),
    onSuccess: invalidate,
  });
  const del = useMutation({ mutationFn: deleteSchedule, onSuccess: invalidate });
  const send = useMutation({ mutationFn: sendNow });

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Reports / Schedules</h1>
          <p className="text-sm text-muted-foreground">
            Scheduled email digests of the All Source Summary.
          </p>
        </div>
        {!readOnly && !creating && !editing && (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent"
          >
            <Plus className="h-3.5 w-3.5" /> New schedule
          </button>
        )}
      </header>

      {creating && (
        <ScheduleForm onClose={() => setCreating(false)} />
      )}
      {editing && (
        <ScheduleForm initial={editing} onClose={() => setEditing(null)} />
      )}

      <div className="overflow-hidden rounded-md border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-xs">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Name
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Cron
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Recipients
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Last run
              </th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                Status
              </th>
              <th className="px-3 py-2"></th>
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
            {data?.length === 0 && !isLoading && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">
                  No schedules yet — create one to email this dashboard on a cadence.
                </td>
              </tr>
            )}
            {data?.map((s) => (
              <tr key={s.id} className="border-t border-border">
                <td className="px-3 py-2">
                  <div className="font-medium">{s.name}</div>
                  <div className="text-xs text-muted-foreground">{s.subject}</div>
                </td>
                <td className="px-3 py-2 font-mono text-xs">{s.cron}</td>
                <td className="px-3 py-2 text-xs">
                  {s.recipients.slice(0, 2).join(", ")}
                  {s.recipients.length > 2 && ` +${s.recipients.length - 2}`}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {s.last_run_at?.slice(0, 19).replace("T", " ") || "—"}
                </td>
                <td className="px-3 py-2">
                  <button
                    type="button"
                    disabled={readOnly}
                    onClick={() => toggleActive.mutate(s)}
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[11px]",
                      s.is_active
                        ? "bg-green-100 text-green-900"
                        : "bg-muted text-muted-foreground",
                      readOnly && "opacity-60",
                    )}
                  >
                    {s.is_active ? "active" : "paused"}
                  </button>
                  {s.last_run_status && s.last_run_status !== "ok" && (
                    <div className="mt-1 text-[10px] text-red-700">
                      {s.last_run_status}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => send.mutate(s.id)}
                        disabled={send.isPending}
                        className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
                      >
                        <Send className="h-3 w-3" /> Send now
                      </button>
                    )}
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => setEditing(s)}
                        className="rounded-md border border-border bg-background px-2 py-1 text-xs hover:bg-accent"
                      >
                        Edit
                      </button>
                    )}
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => {
                          if (confirm(`Delete schedule "${s.name}"?`)) {
                            del.mutate(s.id);
                          }
                        }}
                        className="text-muted-foreground hover:text-red-700"
                        aria-label="Delete schedule"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {send.data && (
        <div
          className={cn(
            "rounded-md border px-3 py-2 text-xs",
            send.data.ok
              ? "border-green-300 bg-green-50 text-green-900"
              : "border-red-300 bg-red-50 text-red-900",
          )}
        >
          {send.data.ok
            ? `Sent ✓ ${send.data.message_id || "(dev mode — no SendGrid key)"}`
            : `Send failed: ${send.data.error}`}
        </div>
      )}
    </div>
  );
}
