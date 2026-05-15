import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Plus, Search, Trash2, X } from "lucide-react";
import {
  type RosterEntry,
  type SfUserResult,
  addToRoster,
  fetchRoster,
  importFromSf,
  removeFromRoster,
  searchSfUsers,
} from "@/api/roster";
import { useReadOnly } from "@/components/auth/ReadOnlyGate";
import { cn } from "@/lib/cn";

function SfUserSearch({
  onAdd,
  alreadyAdded,
}: {
  onAdd: (id: string) => void;
  alreadyAdded: Set<string>;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Pre-fetch the full active-user list once and filter client-side.
  const all = useQuery<SfUserResult[]>({
    queryKey: ["roster", "search-all"],
    queryFn: () => searchSfUsers(""),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  const q = query.trim().toLowerCase();
  const visible = (all.data ?? []).filter((u) => {
    if (alreadyAdded.has(u.id)) return false;
    if (!q) return true;
    return (
      u.name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q)
    );
  });

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2">
        <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search active Salesforce users by name or email…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="h-9 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
        {query && (
          <button type="button" onClick={() => setQuery("")}>
            <X className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-72 overflow-y-auto rounded-md border border-border bg-background shadow-lg">
          {all.isLoading ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">Loading Salesforce users…</p>
          ) : all.isError ? (
            <p className="px-3 py-2 text-sm text-red-700">
              Failed to load users: {(all.error as Error).message}
            </p>
          ) : visible.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">
              {q ? "No matching users" : "No users available"}
            </p>
          ) : (
            <>
              <p className="border-b border-border px-3 py-1 text-xs text-muted-foreground">
                {visible.length}{q ? ` of ${(all.data ?? []).length}` : ""} user(s)
              </p>
              {visible.map((u) => (
                <div
                  key={u.id}
                  className="flex items-center justify-between gap-3 px-3 py-2 hover:bg-accent"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{u.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {u.email}
                      {u.manager_name ? ` · Manager: ${u.manager_name}` : ""}
                      {u.sdr_name ? ` · SDR: ${u.sdr_name}` : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      onAdd(u.id);
                      setQuery("");
                    }}
                    className="flex shrink-0 items-center gap-1 rounded-md border border-border bg-background px-2 py-1 text-xs hover:bg-accent"
                  >
                    <Plus className="h-3 w-3" /> Add
                  </button>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function RosterTable({
  entries,
  onRemove,
  readOnly,
}: {
  entries: RosterEntry[];
  onRemove: (id: string) => void;
  readOnly: boolean;
}) {
  const [filter, setFilter] = useState("");
  const filtered = filter
    ? entries.filter(
        (e) =>
          e.name.toLowerCase().includes(filter.toLowerCase()) ||
          e.email.toLowerCase().includes(filter.toLowerCase()) ||
          e.manager_name.toLowerCase().includes(filter.toLowerCase()),
      )
    : entries;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2">
          <Search className="h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter by name, email, or manager…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-8 w-56 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          {filter && (
            <button type="button" onClick={() => setFilter("")}>
              <X className="h-3 w-3 text-muted-foreground" />
            </button>
          )}
        </div>
        <span className="text-xs text-muted-foreground">{filtered.length} of {entries.length}</span>
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40 text-xs text-muted-foreground">
              <th className="px-3 py-2 text-left font-medium">Name</th>
              <th className="px-3 py-2 text-left font-medium">Email</th>
              <th className="px-3 py-2 text-left font-medium">Manager</th>
              <th className="px-3 py-2 text-left font-medium">SDR</th>
              <th className="px-3 py-2 text-left font-medium">Added By</th>
              {!readOnly && <th className="px-3 py-2" />}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={readOnly ? 5 : 6} className="px-3 py-8 text-center text-muted-foreground">
                  {entries.length === 0
                    ? "No AEs in roster. Click Import or search to add AEs."
                    : "No results match your filter."}
                </td>
              </tr>
            ) : (
              filtered.map((e) => (
                <tr key={e.sf_id} className="border-b border-border/50 last:border-0 hover:bg-muted/20">
                  <td className="px-3 py-2 font-medium">{e.name}</td>
                  <td className="px-3 py-2 text-muted-foreground">{e.email}</td>
                  <td className="px-3 py-2 text-muted-foreground">{e.manager_name || "—"}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {e.sdr_name || (e.sdr_id && e.sdr_id !== "000000000000000" ? e.sdr_id.slice(0, 8) + "…" : "—")}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{e.added_by}</td>
                  {!readOnly && (
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => onRemove(e.sf_id)}
                        title="Remove from roster"
                        className="rounded p-1 text-muted-foreground hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ConfigRosterRoute() {
  const readOnly = useReadOnly();
  const qc = useQueryClient();

  const { data: entries = [], isLoading } = useQuery<RosterEntry[]>({
    queryKey: ["roster"],
    queryFn: fetchRoster,
    staleTime: 60_000,
  });

  const importMut = useMutation({
    mutationFn: importFromSf,
    onSuccess: (res) => {
      void qc.invalidateQueries({ queryKey: ["roster"] });
      void qc.invalidateQueries({ queryKey: ["filters"] });
      alert(`Imported ${res.imported} AE(s) from Salesforce.`);
    },
  });

  const addMut = useMutation({
    mutationFn: addToRoster,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["roster"] });
      void qc.invalidateQueries({ queryKey: ["filters"] });
    },
  });

  const removeMut = useMutation({
    mutationFn: removeFromRoster,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["roster"] });
      void qc.invalidateQueries({ queryKey: ["filters"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold">AE Roster</h2>
          <p className="text-xs text-muted-foreground">
            {entries.length} AE{entries.length !== 1 ? "s" : ""} · Manager and SDR shown for visibility only
          </p>
        </div>
        {!readOnly && (
          <button
            type="button"
            onClick={() => importMut.mutate()}
            disabled={importMut.isPending}
            className={cn(
              "flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50",
            )}
          >
            <Download className={cn("h-4 w-4", importMut.isPending && "animate-pulse")} />
            {importMut.isPending ? "Importing…" : "Import from Salesforce"}
          </button>
        )}
      </div>

      {importMut.isError && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-900">
          Import failed: {(importMut.error as Error).message}
        </div>
      )}

      {!readOnly && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">Add individual AE</p>
          <div className="flex items-start gap-2">
            <SfUserSearch
              onAdd={(id) => addMut.mutate(id)}
              alreadyAdded={new Set(entries.map((e) => e.sf_id))}
            />
            {addMut.isPending && (
              <span className="mt-2 text-xs text-muted-foreground">Adding…</span>
            )}
            {addMut.isError && (
              <span className="mt-2 text-xs text-red-700">
                {(addMut.error as Error).message}
              </span>
            )}
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading roster…</p>
      ) : (
        <RosterTable
          entries={entries}
          onRemove={(id) => removeMut.mutate(id)}
          readOnly={readOnly}
        />
      )}
    </div>
  );
}
