import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { type SoqlEntry, listSoql } from "@/api/soql";
import { SoqlEditor } from "@/components/config/soql/SoqlEditor";
import { SoqlHistory } from "@/components/config/soql/SoqlHistory";
import { SoqlList } from "@/components/config/soql/SoqlList";
import { ReadOnlyGate } from "@/components/auth/ReadOnlyGate";

export function ConfigSoqlRoute() {
  const { data, isLoading } = useQuery<SoqlEntry[]>({
    queryKey: ["soql"],
    queryFn: listSoql,
    staleTime: 30_000,
  });
  const [selected, setSelected] = useState<string | null>(null);

  if (selected == null && data && data.length > 0) {
    setSelected(data[0].col_id);
  }

  return (
    <ReadOnlyGate>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[300px_1fr]">
        <div className="md:h-[calc(100vh-220px)]">
          {isLoading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : (
            data && (
              <SoqlList
                entries={data}
                selected={selected}
                onSelect={setSelected}
              />
            )
          )}
        </div>
        <div className="space-y-6">
          {selected ? (
            <>
              <SoqlEditor colId={selected} />
              <section>
                <h4 className="mb-2 text-sm font-medium">History</h4>
                <SoqlHistory colId={selected} />
              </section>
            </>
          ) : (
            <div className="rounded-md border border-border p-6 text-sm text-muted-foreground">
              Select a column to view its SOQL template.
            </div>
          )}
        </div>
      </div>
    </ReadOnlyGate>
  );
}
