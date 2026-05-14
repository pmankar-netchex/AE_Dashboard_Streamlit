import { useQuery } from "@tanstack/react-query";
import { type SoqlHistoryRow, getSoqlHistory } from "@/api/soql";

export function SoqlHistory({ colId }: { colId: string }) {
  const { data, isLoading } = useQuery<SoqlHistoryRow[]>({
    queryKey: ["soql", colId, "history"],
    queryFn: () => getSoqlHistory(colId),
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="text-xs text-muted-foreground">Loading history…</div>
    );
  }
  if (!data || data.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        No history yet — saves will appear here.
      </div>
    );
  }
  return (
    <ul className="space-y-2">
      {data.map((row) => (
        <li key={row.version} className="rounded-md border border-border px-2 py-2 text-xs">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>{row.saved_at || row.version}</span>
            {row.saved_by && <span>by {row.saved_by}</span>}
          </div>
          <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap font-mono text-[11px]">
            {row.template}
          </pre>
        </li>
      ))}
    </ul>
  );
}
