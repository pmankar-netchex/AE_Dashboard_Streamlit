import { useMutation } from "@tanstack/react-query";
import { Mail, Send } from "lucide-react";
import { useState } from "react";
import { sendOnce } from "@/api/schedules";
import { useFilters } from "@/hooks/useFilters";
import { cn } from "@/lib/cn";

interface Props {
  /** Hide controls when caller wants read-only mode (e.g. for "user" role). */
  readOnly?: boolean;
}

/**
 * One-off "send right now" form — no schedule needed.
 *
 * Pulls the current dashboard filter state from useFilters() so the snapshot
 * reflects whatever the user is looking at. Recipients are entered ad-hoc
 * (comma/newline separated) and nothing is persisted.
 */
export function ImmediateSend({ readOnly = false }: Props) {
  const { filters } = useFilters();
  const [open, setOpen] = useState(false);
  const [recipientsText, setRecipientsText] = useState("");
  const [subject, setSubject] = useState(
    "AE Performance — All Source Summary",
  );

  const send = useMutation({
    mutationFn: () => {
      const recipients = recipientsText
        .split(/[,\n;]/)
        .map((x) => x.trim())
        .filter(Boolean);
      const filterPayload: Record<string, unknown> = {};
      if (filters.manager) filterPayload.manager = filters.manager;
      if (filters.aeIds.length === 1) filterPayload.ae_id = filters.aeIds[0];
      if (filters.period) filterPayload.period = filters.period;
      if (filters.period === "custom") {
        if (filters.from) filterPayload.from = filters.from;
        if (filters.to) filterPayload.to = filters.to;
      }
      return sendOnce({ recipients, subject, filters: filterPayload });
    },
    onSuccess: (res) => {
      if (res.ok) {
        setRecipientsText("");
        setOpen(false);
      }
    },
  });

  if (readOnly) return null;

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent"
      >
        <Mail className="h-3.5 w-3.5" />
        Send immediately
      </button>
    );
  }

  const recipientCount = recipientsText
    .split(/[,\n;]/)
    .map((x) => x.trim())
    .filter(Boolean).length;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        send.mutate();
      }}
      className="space-y-3 rounded-md border border-border bg-muted/20 p-4"
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium">Send the current view now</h4>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Cancel
        </button>
      </div>
      <p className="text-xs text-muted-foreground">
        Renders the All Source Summary using your current filters
        (Manager, AE, Period) and emails it to the recipients below. Nothing
        is saved — this is a one-off send.
      </p>

      <label className="block text-sm">
        <span className="text-muted-foreground">Subject</span>
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="mt-1 block h-8 w-full rounded-md border border-border bg-background px-2"
        />
      </label>

      <label className="block text-sm">
        <span className="text-muted-foreground">
          Recipients (comma-separated)
        </span>
        <textarea
          value={recipientsText}
          onChange={(e) => setRecipientsText(e.target.value)}
          required
          rows={2}
          autoFocus
          className="mt-1 block w-full rounded-md border border-border bg-background px-2 py-1"
          placeholder="cro@example.com, sales-ops@example.com"
        />
      </label>

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={send.isPending || recipientCount === 0}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Send className="h-3.5 w-3.5" />
          {send.isPending
            ? "Sending…"
            : `Send to ${recipientCount || "0"} recipient${recipientCount === 1 ? "" : "s"}`}
        </button>
        {send.data && (
          <span
            className={cn(
              "text-xs",
              send.data.ok ? "text-green-700" : "text-red-700",
            )}
          >
            {send.data.ok
              ? `Sent ✓ ${send.data.message_id || "(dev mode — no SendGrid key)"}`
              : `Failed: ${send.data.error}`}
          </span>
        )}
      </div>
    </form>
  );
}
