import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import type { SoqlEntry } from "@/api/soql";
import { cn } from "@/lib/cn";

interface Props {
  entries: SoqlEntry[];
  selected: string | null;
  onSelect: (colId: string) => void;
}

interface Group {
  section: string;
  entries: SoqlEntry[];
}

export function SoqlList({ entries, selected, onSelect }: Props) {
  const [q, setQ] = useState("");
  const [closedSections, setClosedSections] = useState<Set<string>>(new Set());

  const filtered = useMemo(() => {
    const lower = q.trim().toLowerCase();
    if (!lower) return entries;
    return entries.filter(
      (e) =>
        e.col_id.toLowerCase().includes(lower) ||
        e.display_name.toLowerCase().includes(lower) ||
        e.section.toLowerCase().includes(lower),
    );
  }, [entries, q]);

  // Group by section, preserving registry order (entries arrive in the
  // backend's ALL_COLUMNS order so first-seen section wins).
  const grouped: Group[] = useMemo(() => {
    const byKey = new Map<string, SoqlEntry[]>();
    for (const e of filtered) {
      if (!byKey.has(e.section)) byKey.set(e.section, []);
      byKey.get(e.section)!.push(e);
    }
    return Array.from(byKey.entries()).map(([section, list]) => ({
      section,
      entries: list,
    }));
  }, [filtered]);

  const toggleSection = (s: string): void => {
    setClosedSections((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  return (
    <div className="flex h-full flex-col">
      <div className="relative">
        <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          type="search"
          placeholder="Search…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="h-8 w-full rounded-md border border-border bg-background pl-7 pr-2 text-sm"
        />
      </div>
      <div className="mt-2 flex-1 space-y-2 overflow-auto">
        {grouped.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-muted-foreground">
            No matches.
          </p>
        )}
        {grouped.map(({ section, entries: secEntries }) => {
          const closed = closedSections.has(section);
          return (
            <div key={section} className="rounded-md border border-border">
              <button
                type="button"
                onClick={() => toggleSection(section)}
                className="flex w-full items-center justify-between gap-2 bg-muted/40 px-2 py-1.5 text-left text-xs font-semibold hover:bg-muted"
                aria-expanded={!closed}
              >
                <span className="flex items-center gap-1.5">
                  {closed ? (
                    <ChevronRight className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  {section}
                </span>
                <span className="text-[10px] font-normal text-muted-foreground">
                  {secEntries.length}
                </span>
              </button>
              {!closed && (
                <ul>
                  {secEntries.map((e) => {
                    const active = selected === e.col_id;
                    return (
                      <li key={e.col_id}>
                        <button
                          type="button"
                          onClick={() => onSelect(e.col_id)}
                          className={cn(
                            "flex w-full items-center justify-between gap-2 border-t border-border/40 px-2 py-2 text-left text-xs hover:bg-accent",
                            active && "bg-accent",
                          )}
                        >
                          <span className="flex min-w-0 flex-col gap-0.5">
                            <span className="truncate font-medium text-foreground">
                              {e.display_name}
                            </span>
                            <span className="truncate font-mono text-[10px] text-muted-foreground">
                              {e.col_id}
                            </span>
                            {e.description && (
                              <span className="line-clamp-2 text-[10px] text-muted-foreground/80">
                                {e.description}
                              </span>
                            )}
                          </span>
                          <span className="flex shrink-0 gap-1">
                            {e.has_override && (
                              <span className="rounded bg-primary/10 px-1 text-[10px] uppercase text-primary">
                                ovr
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
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
