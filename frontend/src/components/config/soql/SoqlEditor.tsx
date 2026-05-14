import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type SoqlEntry,
  type SoqlTestResult,
  getSoql,
  testSoql,
  updateSoql,
} from "@/api/soql";
import { useReadOnly } from "@/components/auth/ReadOnlyGate";
import { useAes } from "@/hooks/useDashboard";
import { useMe } from "@/hooks/useMe";
import { useFilters } from "@/hooks/useFilters";
import { fmt } from "@/lib/formatters";
import { cn } from "@/lib/cn";

interface Props {
  colId: string;
}

export function SoqlEditor({ colId }: Props) {
  const readOnly = useReadOnly();
  const { data: me } = useMe();
  const writesEnabled = me?.flags.soql_writes_enabled ?? false;
  const qc = useQueryClient();
  const { filters } = useFilters();

  const entry = useQuery<SoqlEntry>({
    queryKey: ["soql", colId],
    queryFn: () => getSoql(colId),
    enabled: !!colId,
  });

  const [draft, setDraft] = useState<string>("");
  const [testAeId, setTestAeId] = useState<string | null>(null);
  const [lastTestedDraft, setLastTestedDraft] = useState<string>("");
  const [testResult, setTestResult] = useState<SoqlTestResult | null>(null);

  // Hydrate draft when entry loads or col changes
  useEffect(() => {
    if (entry.data) {
      setDraft(entry.data.template_active);
      setLastTestedDraft("");
      setTestResult(null);
    }
  }, [entry.data, colId]);

  const aes = useAes(filters.manager);
  const aeOptions = aes.data ?? [];

  const dirty = useMemo(
    () => entry.data ? draft !== entry.data.template_active : false,
    [draft, entry.data],
  );
  const testedClean = dirty && draft === lastTestedDraft && testResult?.ok;

  const testMut = useMutation({
    mutationFn: () =>
      testSoql(colId, {
        template: draft,
        ae_user_id: testAeId,
        period: filters.period,
      }),
    onSuccess: (res) => {
      setTestResult(res);
      setLastTestedDraft(draft);
    },
  });

  const saveMut = useMutation({
    mutationFn: () => updateSoql(colId, draft),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["soql"] });
      void qc.invalidateQueries({ queryKey: ["soql", colId] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (entry.isLoading || !entry.data) {
    return (
      <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
        Loading template…
      </div>
    );
  }

  const e = entry.data;
  const saveDisabled =
    readOnly || !writesEnabled || !dirty || saveMut.isPending || !testedClean;

  return (
    <div className="flex flex-col gap-3">
      <header>
        <div className="flex items-baseline gap-2">
          <code className="font-mono text-sm">{e.col_id}</code>
          <h3 className="text-sm font-medium">{e.display_name}</h3>
          <span className="text-xs text-muted-foreground">• {e.section}</span>
        </div>
        {e.description && (
          <p className="mt-1 text-xs text-muted-foreground">{e.description}</p>
        )}
        {e.aggregation && (
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            Aggregation: {e.aggregation}
          </p>
        )}
      </header>

      {!writesEnabled && (
        <div className="rounded-md border border-yellow-300 bg-yellow-50 px-3 py-2 text-xs text-yellow-900">
          Writes to the production SOQL store are disabled
          (<code>ALLOW_PROD_QUERY_WRITES=false</code>). View-only mode.
        </div>
      )}

      <textarea
        value={draft}
        readOnly={readOnly || !writesEnabled}
        onChange={(ev) => setDraft(ev.target.value)}
        spellCheck={false}
        rows={14}
        className="rounded-md border border-border bg-background px-2 py-1.5 font-mono text-xs"
      />

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <label className="flex items-center gap-1">
          <span className="text-muted-foreground">Test as AE:</span>
          <select
            className="h-7 rounded-md border border-border bg-background px-1"
            value={testAeId ?? ""}
            onChange={(ev) => setTestAeId(ev.target.value || null)}
          >
            <option value="">(none — aggregate over all)</option>
            {aeOptions.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => testMut.mutate()}
          disabled={readOnly || testMut.isPending}
          className="h-7 rounded-md border border-border bg-background px-2 hover:bg-accent disabled:opacity-50"
        >
          {testMut.isPending ? "Testing…" : "Test query"}
        </button>
        <button
          type="button"
          onClick={() => saveMut.mutate()}
          disabled={saveDisabled}
          title={
            !writesEnabled
              ? "Writes disabled"
              : !dirty
                ? "No changes"
                : !testedClean
                  ? "Test before saving"
                  : ""
          }
          className={cn(
            "h-7 rounded-md px-3 text-primary-foreground",
            saveDisabled
              ? "bg-primary/40"
              : "bg-primary hover:bg-primary/90",
          )}
        >
          {saveMut.isPending ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={() => setDraft(e.template_default)}
          disabled={readOnly || !writesEnabled}
          className="h-7 rounded-md border border-border bg-background px-2 hover:bg-accent disabled:opacity-50"
        >
          Reset to default
        </button>
        {dirty && (
          <span className="text-muted-foreground">• unsaved changes</span>
        )}
      </div>

      {testResult && (
        <div
          className={cn(
            "rounded-md border px-3 py-2 text-xs",
            testResult.ok
              ? "border-green-300 bg-green-50 text-green-900"
              : "border-red-300 bg-red-50 text-red-900",
          )}
        >
          {testResult.ok ? (
            <div className="space-y-1">
              <div>
                <strong>Value:</strong> {fmt(testResult.value, "number")}
                {" • "}
                <strong>Total size:</strong> {testResult.total_size}
              </div>
              <details>
                <summary className="cursor-pointer text-muted-foreground">
                  Resolved SOQL
                </summary>
                <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap font-mono text-[11px]">
                  {testResult.soql}
                </pre>
              </details>
            </div>
          ) : (
            <span>{testResult.error}</span>
          )}
        </div>
      )}

      {saveMut.isError && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900">
          {(saveMut.error as Error).message}
        </div>
      )}
    </div>
  );
}
