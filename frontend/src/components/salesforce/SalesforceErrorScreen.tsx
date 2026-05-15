import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { AlertTriangle, ExternalLink, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { refreshSalesforceToken } from "@/api/salesforce";
import { useReadOnly } from "@/components/auth/ReadOnlyGate";
import { formatInTz, useTz } from "@/lib/datetime";
import type { ApiError } from "@/api/client";

interface Props {
  error: ApiError;
  /** Page title to show above the error card, e.g. "Dashboard unavailable". */
  title?: string;
}

const REMEDIATION_STEPS = [
  {
    label: "Verify the Connected App is still active in Salesforce",
    detail:
      "Setup → App Manager → find the integration app → confirm OAuth policies allow the Client Credentials flow.",
  },
  {
    label: "Confirm the integration user is enabled",
    detail:
      "Setup → Users → check IsActive, profile, and that no IP login range / session policy is blocking the request.",
  },
  {
    label: "Re-fetch the token from /config/salesforce",
    detail:
      "If credentials are intact, click Re-fetch token below to mint a fresh access token. Most transient errors clear immediately.",
  },
  {
    label: "If still failing, rotate the Connected App secret",
    detail:
      "Generate a new consumer secret in Salesforce and update SF_CLIENT_SECRET, then restart the API.",
  },
];

export function SalesforceErrorScreen({ error, title }: Props) {
  const readOnly = useReadOnly();
  const tz = useTz();
  const qc = useQueryClient();
  const sf = error.salesforce;

  const refresh = useMutation({
    mutationFn: refreshSalesforceToken,
    onSuccess: (res) => {
      if (res.ok) {
        toast.success(`Salesforce token refreshed · ${res.latency_ms}ms`);
        void qc.invalidateQueries();
      } else {
        toast.error(`Token refresh failed: ${res.error ?? "unknown error"}`);
      }
    },
    onError: (err) => toast.error(`Token refresh failed: ${(err as Error).message}`),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["salesforce", "status"] });
    },
  });

  return (
    <div className="mx-auto max-w-2xl py-8">
      {title && <h2 className="mb-3 text-lg font-semibold">{title}</h2>}
      <div className="overflow-hidden rounded-lg border border-amber-300 bg-amber-50/40">
        <div className="flex items-start gap-3 border-b border-amber-200 bg-amber-100/60 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-700" />
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-amber-900">
              Salesforce session expired or rejected
            </h3>
            <p className="mt-1 break-words text-xs text-amber-900/80">
              {error.message}
            </p>
          </div>
        </div>

        <dl className="grid grid-cols-3 gap-x-4 gap-y-1.5 border-b border-amber-200 px-4 py-3 text-xs">
          <dt className="text-muted-foreground">Instance</dt>
          <dd className="col-span-2 break-all">{sf?.instance_url ?? "—"}</dd>
          <dt className="text-muted-foreground">Last success</dt>
          <dd className="col-span-2">{formatInTz(sf?.last_success_at, tz)}</dd>
          <dt className="text-muted-foreground">Error code</dt>
          <dd className="col-span-2 font-mono">{sf?.error_code ?? "unknown"}</dd>
        </dl>

        <div className="p-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Steps to fix
          </p>
          <ol className="space-y-2.5 text-sm">
            {REMEDIATION_STEPS.map((step, i) => (
              <li key={step.label} className="flex gap-2.5">
                <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-amber-200 text-[11px] font-semibold text-amber-900">
                  {i + 1}
                </span>
                <div>
                  <div className="font-medium">{step.label}</div>
                  <div className="text-xs text-muted-foreground">{step.detail}</div>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => refresh.mutate()}
              disabled={readOnly || refresh.isPending}
              title={readOnly ? "Admin role required" : ""}
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
            >
              <RefreshCw
                className={refresh.isPending ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"}
              />
              Re-fetch token
            </button>
            <Link
              to="/config/salesforce"
              className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Salesforce Connection
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
