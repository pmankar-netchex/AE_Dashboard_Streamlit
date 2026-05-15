import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { type Schedule, createSchedule, updateSchedule } from "@/api/schedules";
import { useMe } from "@/hooks/useMe";
import {
  DEFAULT_SCHEDULE,
  DOW_LABELS,
  type FriendlySchedule,
  type Frequency,
  describeSchedule,
  makeCron,
  parseCron,
} from "@/lib/cron";
import { cn } from "@/lib/cn";

interface Props {
  initial?: Schedule;
  onClose: () => void;
}

export function ScheduleForm({ initial, onClose }: Props) {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const tz = me?.flags.scheduler_tz ?? "UTC";

  const [name, setName] = useState(initial?.name ?? "");
  const [subject, setSubject] = useState(
    initial?.subject ?? "AE Performance — All Source Summary",
  );
  const [recipientsText, setRecipientsText] = useState(
    initial ? initial.recipients.join(", ") : "",
  );
  const [schedule, setSchedule] = useState<FriendlySchedule>(
    initial ? parseCron(initial.cron) : DEFAULT_SCHEDULE,
  );

  // Keep the raw cron field in sync with the friendly inputs unless the
  // user is in custom mode.
  useEffect(() => {
    if (schedule.frequency !== "custom") {
      const next = makeCron(schedule);
      if (next !== schedule.raw) {
        setSchedule((s) => ({ ...s, raw: next }));
      }
    }
  }, [schedule.frequency, schedule.hour, schedule.minute, schedule.daysOfWeek, schedule.dayOfMonth]); // eslint-disable-line react-hooks/exhaustive-deps

  const finalCron = makeCron(schedule);

  const create = useMutation({
    mutationFn: () =>
      createSchedule({
        name,
        cron: finalCron,
        subject,
        recipients: parseRecipients(recipientsText),
        is_active: true,
      }),
    onSuccess: (s) => {
      void qc.invalidateQueries({ queryKey: ["schedules"] });
      onClose();
      toast.success(`Created schedule "${s.name}"`);
    },
    onError: (err) => toast.error(`Create failed: ${(err as Error).message}`),
  });

  const update = useMutation({
    mutationFn: () =>
      updateSchedule(initial!.id, {
        name,
        cron: finalCron,
        subject,
        recipients: parseRecipients(recipientsText),
      }),
    onSuccess: (s) => {
      void qc.invalidateQueries({ queryKey: ["schedules"] });
      onClose();
      toast.success(`Saved schedule "${s.name}"`);
    },
    onError: (err) => toast.error(`Save failed: ${(err as Error).message}`),
  });

  const m = initial ? update : create;
  const summary = describeSchedule(schedule, tz);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
      className="space-y-4 rounded-md border border-border bg-muted/20 p-4"
    >
      <h4 className="font-medium">
        {initial ? "Edit schedule" : "New schedule"}
      </h4>

      <label className="block text-sm">
        <span className="text-muted-foreground">Name</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="mt-1 block h-8 w-full rounded-md border border-border bg-background px-2"
        />
      </label>

      <label className="block text-sm">
        <span className="text-muted-foreground">Subject</span>
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="mt-1 block h-8 w-full rounded-md border border-border bg-background px-2"
        />
      </label>

      <fieldset className="space-y-2 text-sm">
        <legend className="text-muted-foreground">Cadence</legend>

        {/* Frequency picker */}
        <div className="inline-flex overflow-hidden rounded-md border border-border">
          {(["daily", "weekdays", "weekly", "monthly", "custom"] as Frequency[]).map(
            (f) => (
              <button
                key={f}
                type="button"
                onClick={() => setSchedule((s) => ({ ...s, frequency: f }))}
                className={cn(
                  "px-2.5 py-1 text-xs capitalize",
                  schedule.frequency === f
                    ? "bg-primary text-primary-foreground"
                    : "bg-background hover:bg-accent",
                )}
              >
                {f}
              </button>
            ),
          )}
        </div>

        {/* Time picker — always shown except for custom */}
        {schedule.frequency !== "custom" && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">At</span>
            <input
              type="time"
              value={`${String(schedule.hour).padStart(2, "0")}:${String(
                schedule.minute,
              ).padStart(2, "0")}`}
              onChange={(e) => {
                const [hh, mm] = e.target.value.split(":");
                setSchedule((s) => ({
                  ...s,
                  hour: Number(hh) || 0,
                  minute: Number(mm) || 0,
                }));
              }}
              className="h-8 rounded-md border border-border bg-background px-2 text-xs"
            />
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              Times are interpreted in <strong className="font-medium">{tz}</strong>
            </span>
          </div>
        )}

        {/* Frequency-specific extras */}
        {schedule.frequency === "weekly" && (
          <div className="flex flex-wrap items-center gap-1">
            <span className="mr-1 text-xs text-muted-foreground">On</span>
            {DOW_LABELS.map((label, idx) => {
              const checked = schedule.daysOfWeek.includes(idx);
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() =>
                    setSchedule((s) => {
                      const next = checked
                        ? s.daysOfWeek.filter((d) => d !== idx)
                        : [...s.daysOfWeek, idx];
                      return { ...s, daysOfWeek: next };
                    })
                  }
                  className={cn(
                    "h-7 w-9 rounded-md border text-xs",
                    checked
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-background hover:bg-accent",
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}

        {schedule.frequency === "monthly" && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">On day</span>
            <input
              type="number"
              min={1}
              max={28}
              value={schedule.dayOfMonth}
              onChange={(e) =>
                setSchedule((s) => ({
                  ...s,
                  dayOfMonth: Math.min(28, Math.max(1, Number(e.target.value) || 1)),
                }))
              }
              className="h-8 w-16 rounded-md border border-border bg-background px-2 text-xs"
            />
            <span className="text-xs text-muted-foreground">of the month (1–28)</span>
          </div>
        )}

        {schedule.frequency === "custom" && (
          <div className="space-y-1">
            <input
              value={schedule.raw}
              onChange={(e) =>
                setSchedule((s) => ({ ...s, raw: e.target.value }))
              }
              required
              className="block h-8 w-full rounded-md border border-border bg-background px-2 font-mono text-xs"
              placeholder="0 9 * * 1-5"
            />
            <p className="text-[11px] text-muted-foreground">
              5-field cron (minute hour day-of-month month day-of-week).
            </p>
          </div>
        )}

        {/* Summary + the actual cron, in case anyone wants to see */}
        <div className="rounded-md border border-border bg-background px-3 py-2 text-xs">
          <div className="font-medium text-foreground">{summary}</div>
          <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">
            cron: <code>{finalCron}</code>
          </div>
        </div>
      </fieldset>

      <label className="block text-sm">
        <span className="text-muted-foreground">
          Recipients (comma-separated)
        </span>
        <textarea
          value={recipientsText}
          onChange={(e) => setRecipientsText(e.target.value)}
          required
          rows={2}
          className="mt-1 block w-full rounded-md border border-border bg-background px-2 py-1"
          placeholder="cro@example.com, sales-ops@example.com"
        />
      </label>

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={m.isPending}
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {m.isPending ? "Saving…" : initial ? "Save" : "Create"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent"
        >
          Cancel
        </button>
        {m.isError && (
          <span className="text-xs text-red-700">{(m.error as Error).message}</span>
        )}
      </div>
    </form>
  );
}

function parseRecipients(s: string): string[] {
  return s
    .split(/[,\n;]/)
    .map((x) => x.trim())
    .filter(Boolean);
}
