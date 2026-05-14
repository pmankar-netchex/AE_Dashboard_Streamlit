import { useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import type { SoqlEntry } from "@/api/soql";

interface Props {
  entries: SoqlEntry[];
  selected: string | null;
  onSelect: (colId: string) => void;
}

export function SoqlList({ entries, selected, onSelect }: Props) {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => {
    const lower = q.trim().toLowerCase();
    if (!lower) return entries;
    return entries.filter(
      (e) =>
        e.col_id.toLowerCase().includes(lower) ||
        e.display_name.toLowerCase().includes(lower),
    );
  }, [entries, q]);

  return (
    <div className="flex h-full flex-col">
      <input
        type="search"
        placeholder="Search col_id or name…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="h-8 rounded-md border border-border bg-background px-2 text-sm"
      />
      <ul className="mt-2 flex-1 overflow-auto rounded-md border border-border">
        {filtered.map((e) => {
          const active = selected === e.col_id;
          return (
            <li key={e.col_id}>
              <button
                type="button"
                onClick={() => onSelect(e.col_id)}
                className={cn(
                  "flex w-full items-center justify-between px-2 py-1.5 text-left text-xs hover:bg-accent",
                  active && "bg-accent",
                )}
              >
                <span className="flex flex-col">
                  <span className="font-mono text-[11px]">{e.col_id}</span>
                  <span className="truncate text-muted-foreground">
                    {e.display_name}
                  </span>
                </span>
                <span className="flex shrink-0 gap-1">
                  {e.has_override && (
                    <span className="rounded bg-primary/10 px-1 text-[10px] uppercase text-primary">
                      override
                    </span>
                  )}
                  {e.blocked && (
                    <span className="rounded bg-yellow-100 px-1 text-[10px] uppercase text-yellow-800">
                      pending
                    </span>
                  )}
                  {e.computed && (
                    <span className="rounded bg-muted px-1 text-[10px] uppercase text-muted-foreground">
                      computed
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
