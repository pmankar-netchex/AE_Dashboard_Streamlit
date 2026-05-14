import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { type Schedule, createSchedule, updateSchedule } from "@/api/schedules";

const PRESETS = [
  { label: "Daily 9am", cron: "0 9 * * *" },
  { label: "Weekdays 9am", cron: "0 9 * * 1-5" },
  { label: "Mondays 9am", cron: "0 9 * * 1" },
  { label: "Monthly 1st 9am", cron: "0 9 1 * *" },
];

interface Props {
  initial?: Schedule;
  onClose: () => void;
}

export function ScheduleForm({ initial, onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState(initial?.name ?? "");
  const [cron, setCron] = useState(initial?.cron ?? PRESETS[0].cron);
  const [subject, setSubject] = useState(
    initial?.subject ?? "AE Performance — All Source Summary",
  );
  const [recipientsText, setRecipientsText] = useState(
    initial ? initial.recipients.join(", ") : "",
  );

  const create = useMutation({
    mutationFn: () =>
      createSchedule({
        name,
        cron,
        subject,
        recipients: parseRecipients(recipientsText),
        is_active: true,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["schedules"] });
      onClose();
    },
  });

  const update = useMutation({
    mutationFn: () =>
      updateSchedule(initial!.id, {
        name,
        cron,
        subject,
        recipients: parseRecipients(recipientsText),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["schedules"] });
      onClose();
    },
  });

  const m = initial ? update : create;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        m.mutate();
      }}
      className="space-y-3 rounded-md border border-border bg-muted/20 p-4"
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
      <div className="text-sm">
        <span className="text-muted-foreground">Cadence</span>
        <div className="mt-1 flex flex-wrap items-center gap-1">
          {PRESETS.map((p) => (
            <button
              key={p.cron}
              type="button"
              onClick={() => setCron(p.cron)}
              className="rounded-md border border-border bg-background px-2 py-1 text-xs hover:bg-accent"
            >
              {p.label}
            </button>
          ))}
        </div>
        <input
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          required
          className="mt-2 block h-8 w-full rounded-md border border-border bg-background px-2 font-mono text-xs"
          placeholder="0 9 * * 1-5"
        />
        <p className="mt-1 text-[11px] text-muted-foreground">
          Standard 5-field cron (min hour dom mon dow).
        </p>
      </div>
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
