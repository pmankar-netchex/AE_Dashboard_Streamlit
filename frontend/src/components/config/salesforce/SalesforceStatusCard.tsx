import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Circle, RefreshCw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import {
  type SalesforceStatus,
  type SalesforceUserInfoProbe,
  type UserRoleSample,
  fetchSalesforceStatus,
  fetchUserInfoProbe,
  fetchUserRoles,
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

function TokenValidityProbe({ enabled }: { enabled: boolean }) {
  const { data, isFetching, refetch, isError, error } =
    useQuery<SalesforceUserInfoProbe>({
      queryKey: ["salesforce", "userinfo"],
      queryFn: fetchUserInfoProbe,
      enabled,
      retry: false,
      staleTime: 30_000,
    });

  const ok = data?.ok === true;
  const failed = data && data.ok === false;

  return (
    <div
      className={cn(
        "rounded-md border p-3 text-sm",
        ok && "border-green-300 bg-green-50/50",
        failed && "border-red-300 bg-red-50/50",
        !data && "border-border",
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-medium text-muted-foreground">
          <ShieldCheck className="h-3.5 w-3.5" />
          Run-As identity (token validity)
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1 rounded border border-border bg-background px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
        >
          <RefreshCw className={cn("h-3 w-3", isFetching && "animate-spin")} />
          {data ? "Re-probe" : "Probe"}
        </button>
      </div>

      {isError ? (
        <p className="mt-2 text-xs text-red-700">
          {(error as Error).message ?? "Probe failed"}
        </p>
      ) : isFetching && !data ? (
        <p className="mt-2 text-xs text-muted-foreground">
          Calling /services/oauth2/userinfo…
        </p>
      ) : ok && data ? (
        <dl className="mt-2 grid grid-cols-3 gap-x-3 gap-y-1 text-xs">
          <dt className="text-muted-foreground">User</dt>
          <dd className="col-span-2 break-all font-medium">
            {data.display_name ?? data.username ?? "—"}
          </dd>
          <dt className="text-muted-foreground">Username</dt>
          <dd className="col-span-2 break-all">{data.username ?? "—"}</dd>
          <dt className="text-muted-foreground">Email</dt>
          <dd className="col-span-2 break-all">{data.email ?? "—"}</dd>
          <dt className="text-muted-foreground">User Id</dt>
          <dd className="col-span-2 font-mono">{data.user_id ?? "—"}</dd>
          <dt className="text-muted-foreground">Org Id</dt>
          <dd className="col-span-2 font-mono">{data.organization_id ?? "—"}</dd>
          <dt className="text-muted-foreground">Latency</dt>
          <dd className="col-span-2">{data.latency_ms}ms</dd>
        </dl>
      ) : failed ? (
        <div className="mt-2 space-y-2">
          <div className="flex items-start gap-2 text-xs text-red-800">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
            <div className="min-w-0">
              <div className="font-medium">
                Token minted ok but Salesforce rejected it
                {data.status_code ? ` (HTTP ${data.status_code})` : ""}
              </div>
              <div className="break-words text-red-800/80">{data.error}</div>
            </div>
          </div>
          <div className="rounded border border-red-200 bg-white px-2.5 py-2 text-xs text-foreground">
            <div className="mb-1 font-medium">Likely Connected App issue:</div>
            <ul className="list-disc space-y-0.5 pl-4 text-muted-foreground">
              <li>
                "Run As" user not set on the Connected App's Client Credentials
                Flow section (Setup → App Manager → Edit → OAuth Policies)
              </li>
              <li>Run-As user is inactive or lost "API Enabled" permission</li>
              <li>
                IP login range on the user's profile blocks the API caller's
                egress IP
              </li>
              <li>Connected App missing the <code>api</code> OAuth scope</li>
            </ul>
          </div>
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          Click Probe to confirm the cached token authenticates against
          /oauth2/userinfo and to see which Salesforce user it represents.
        </p>
      )}
    </div>
  );
}

function UserRoleDiagnostic() {
  const { data, isLoading, refetch, isFetching } = useQuery<UserRoleSample>({
    queryKey: ["salesforce", "user-roles"],
    queryFn: fetchUserRoles,
    enabled: false,
    retry: false,
  });

  return (
    <div className="rounded-md border border-border p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium text-muted-foreground">AE Role Diagnostic</span>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-1 rounded border border-border bg-background px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
        >
          <RefreshCw className={cn("h-3 w-3", isFetching && "animate-spin")} />
          {data ? "Re-run" : "Run check"}
        </button>
      </div>
      {isLoading || isFetching ? (
        <p className="mt-2 text-xs text-muted-foreground">Querying Salesforce…</p>
      ) : data ? (
        <div className="mt-2 space-y-1.5">
          <p className="text-xs text-muted-foreground">
            Active users in org: <strong>{data.total_active_users}</strong>
          </p>
          {data.error ? (
            <p className="text-xs text-red-700">{data.error}</p>
          ) : data.role_values.length === 0 ? (
            <p className="text-xs text-amber-700">
              No User_Role_Formula__c values found — field may be empty or missing.
            </p>
          ) : (
            <>
              <p className="text-xs text-muted-foreground">
                Distinct <code>User_Role_Formula__c</code> values (first 200 users):
              </p>
              <ul className="mt-1 space-y-0.5">
                {data.role_values.map((v) => (
                  <li key={v} className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
                    {v}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          Click "Run check" to see what role values exist — helps diagnose why no AEs appear.
        </p>
      )}
    </div>
  );
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
    onSuccess: (res) => {
      if (res.ok) toast.success(`Salesforce token refreshed · ${res.latency_ms}ms`);
      else toast.error(`Token refresh failed: ${res.error ?? "unknown error"}`);
    },
    onError: (err) => toast.error(`Token refresh failed: ${(err as Error).message}`),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["salesforce", "status"] });
      void qc.invalidateQueries({ queryKey: ["salesforce", "userinfo"] });
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
        <dt className="text-muted-foreground">Token origin</dt>
        <dd className="break-all">{data.token_origin ?? "—"}</dd>
        <dt className="text-muted-foreground">Token age</dt>
        <dd>{ageLabel(data.age_seconds)}</dd>
        <dt className="text-muted-foreground">Last success</dt>
        <dd>{formatInTz(data.last_success_at, tz)}</dd>
      </dl>

      {data.token_origin_is_generic && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <strong>Token minted at a generic login URL.</strong> CC-flow tokens
          minted at <code>{data.token_origin}</code> are rejected by Salesforce
          REST APIs with <code>INVALID_SESSION_ID</code>. Set{" "}
          <code>SF_LOGIN_URL</code> to the org's My Domain URL
          (e.g. <code>https://netchex.my.salesforce.com</code>) and redeploy.
        </div>
      )}

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

      <TokenValidityProbe enabled={connected} />
      <UserRoleDiagnostic />
    </div>
  );
}
