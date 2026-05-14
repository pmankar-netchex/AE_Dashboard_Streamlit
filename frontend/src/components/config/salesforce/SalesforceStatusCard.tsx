import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, RefreshCw } from "lucide-react";
import {
  type SalesforceStatus,
  fetchSalesforceStatus,
  refreshSalesforceToken,
} from "@/api/salesforce";
import { useReadOnly } from "@/components/auth/ReadOnlyGate";
import { formatInTz, useTz } from "@/lib/datetime";
import { cn } from "@/lib/cn";

function ageLabel(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export function SalesforceStatusCard() {
  const readOnly = useReadOnly();
  const tz = useTz();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<SalesforceStatus>({
    queryKey: ["salesforce", "status"],
    queryFn: fetchSalesforceStatus,
    refetchInterval: 30_000,
  });

  const refresh = useMutation({
    mutationFn: refreshSalesforceToken,
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["salesforce", "status"] });
    },
  });

  if (isLoading || !data) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        Loading Salesforce status…
      </div>
    );
  }

  const connected = data.configured && data.has_token;
  const Icon = connected ? CheckCircle2 : Circle;

  return (
    <div className="space-y-4 rounded-lg border border-border p-6">
      <header className="flex items-center justify-between">
        <h3 className="text-base font-semibold">Salesforce Connection</h3>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs",
            connected
              ? "bg-green-100 text-green-900"
              : "bg-amber-100 text-amber-900",
          )}
        >
          <Icon className="h-3.5 w-3.5" />
          {connected ? "Connected" : data.configured ? "Not initialized" : "Not configured"}
        </span>
      </header>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Flow</dt>
        <dd>OAuth 2.0 Client Credentials</dd>
        <dt className="text-muted-foreground">Instance URL</dt>
        <dd className="break-all">{data.instance_url ?? "—"}</dd>
        <dt className="text-muted-foreground">Token age</dt>
        <dd>{ageLabel(data.age_seconds)}</dd>
        <dt className="text-muted-foreground">Last success</dt>
        <dd>{formatInTz(data.last_success_at, tz)}</dd>
      </dl>

      {data.last_error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900">
          <strong>Last error:</strong> {data.last_error}
        </div>
      )}

      <div>
        <button
          type="button"
          onClick={() => refresh.mutate()}
          disabled={readOnly || refresh.isPending}
          title={readOnly ? "Admin role required" : ""}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50",
          )}
        >
          <RefreshCw className={cn("h-3.5 w-3.5", refresh.isPending && "animate-spin")} />
          Re-fetch token
        </button>
        {refresh.data && (
          <span className="ml-3 text-xs text-muted-foreground">
            {refresh.data.ok
              ? `ok • ${refresh.data.latency_ms}ms`
              : `error • ${refresh.data.error}`}
          </span>
        )}
      </div>
    </div>
  );
}
