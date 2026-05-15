import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, Search, Trash2, UserPlus, X } from "lucide-react";
import { toast } from "sonner";
import {
  type RosterEntry,
  type SfUserResult,
  addToRoster,
  fetchRoster,
  importFromSf,
  removeFromRoster,
  searchSfUsers,
} from "@/api/roster";
import { isSalesforceSessionError } from "@/api/client";
import { useReadOnly } from "@/components/auth/ReadOnlyGate";
import { SalesforceErrorScreen } from "@/components/salesforce/SalesforceErrorScreen";
import { cn } from "@/lib/cn";

function AddAEDialog({
  alreadyAdded,
  onAdd,
  isAdding,
  pendingId,
}: {
  alreadyAdded: Set<string>;
  onAdd: (id: string) => void;
  isAdding: boolean;
  pendingId: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  // Pre-fetch active SF users when the dialog opens; cached for 5 min.
  const all = useQuery<SfUserResult[]>({
    queryKey: ["roster", "search-all"],
    queryFn: () => searchSfUsers(""),
    enabled: open,
    staleTime: 5 * 60_000,
  });

  const q = query.trim().toLowerCase();
  const visible = (all.data ?? []).filter((u) => {
    if (alreadyAdded.has(u.sf_id)) return false;
    if (!q) return true;
    return (
      u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
    );
  });

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setQuery("");
      }}
    >
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2"
        >
          <UserPlus className="h-4 w-4" />
          Add AE
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          aria-describedby="add-ae-desc"
          className={cn(
            "fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[92vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
            "duration-150",
          )}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
            <div>
              <Dialog.Title className="text-base font-semibold">
                Add AE to roster
              </Dialog.Title>
              <Dialog.Description id="add-ae-desc" className="mt-0.5 text-xs text-muted-foreground">
                Pick active Salesforce users. Clicking Add inserts them
                immediately — you can add several before closing.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close"
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          {/* Search */}
          <div className="border-b border-border bg-muted/30 px-5 py-3">
            <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2 focus-within:ring-2 focus-within:ring-primary/30">
              <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
              {/* autoFocus is acceptable inside a modal — focus is already trapped here */}
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name or email…"
                autoFocus
                className="h-10 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  aria-label="Clear search"
                  className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* List */}
          <div className="min-h-0 flex-1 overflow-y-auto">
            {all.isLoading ? (
              <div className="flex items-center justify-center gap-2 px-5 py-12 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading Salesforce users…
              </div>
            ) : all.isError ? (
              isSalesforceSessionError(all.error) ? (
                <div className="px-3 py-3">
                  <SalesforceErrorScreen error={all.error} />
                </div>
              ) : (
                <div className="m-5 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                  Failed to load users: {(all.error as Error).message}
                </div>
              )
            ) : visible.length === 0 ? (
              <div className="px-5 py-12 text-center text-sm text-muted-foreground">
                {q
                  ? `No active SF users match "${query}".`
                  : "Every active SF user is already in the roster."}
              </div>
            ) : (
              <ul role="list" className="divide-y divide-border">
                {visible.map((u) => {
                  const justAddedPending = isAdding && pendingId === u.sf_id;
                  return (
                    <li key={u.sf_id}>
                      <button
                        type="button"
                        onClick={() => onAdd(u.sf_id)}
                        disabled={isAdding}
                        className={cn(
                          "flex w-full items-center justify-between gap-3 px-5 py-3 text-left",
                          "hover:bg-accent focus-visible:bg-accent focus-visible:outline-none",
                          "disabled:cursor-not-allowed disabled:opacity-60",
                        )}
                      >
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{u.name}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {u.email}
                            {u.manager_name ? ` · Manager: ${u.manager_name}` : ""}
                            {u.sdr_name ? ` · SDR: ${u.sdr_name}` : ""}
                          </p>
                        </div>
                        <span
                          className={cn(
                            "inline-flex h-7 shrink-0 items-center gap-1 rounded-md border px-2 text-xs font-medium",
                            justAddedPending
                              ? "border-primary/30 bg-primary/5 text-primary"
                              : "border-border bg-background text-foreground",
                          )}
                        >
                          {justAddedPending ? (
                            <>
                              <Loader2 className="h-3 w-3 animate-spin" />
                              Adding…
                            </>
                          ) : (
                            <>
                              <UserPlus className="h-3 w-3" />
                              Add
                            </>
                          )}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-border bg-muted/20 px-5 py-3 text-xs">
            <span className="text-muted-foreground tabular-nums">
              {all.data
                ? `${visible.length}${q ? ` of ${(all.data ?? []).filter((u) => !alreadyAdded.has(u.sf_id)).length}` : ""} eligible · ${alreadyAdded.size} already in roster`
                : ""}
            </span>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              >
                Done
              </button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
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
        <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2 focus-within:ring-2 focus-within:ring-primary/30">
          <Search className="h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Filter roster by name, email, or manager…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-8 w-64 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          {filter && (
            <button
              type="button"
              onClick={() => setFilter("")}
              aria-label="Clear filter"
            >
              <X className="h-3 w-3 text-muted-foreground" />
            </button>
          )}
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {filtered.length} of {entries.length}
        </span>
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
                <td
                  colSpan={readOnly ? 5 : 6}
                  className="px-3 py-8 text-center text-muted-foreground"
                >
                  {entries.length === 0
                    ? "No AEs in roster. Use Add AE or Import from Salesforce."
                    : "No results match your filter."}
                </td>
              </tr>
            ) : (
              filtered.map((e) => (
                <tr
                  key={e.sf_id}
                  className="border-b border-border/50 last:border-0 hover:bg-muted/20"
                >
                  <td className="px-3 py-2 font-medium">{e.name}</td>
                  <td className="px-3 py-2 text-muted-foreground">{e.email}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {e.manager_name || "—"}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {e.sdr_name ||
                      (e.sdr_id && e.sdr_id !== "000000000000000"
                        ? e.sdr_id.slice(0, 8) + "…"
                        : "—")}
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {e.added_by}
                  </td>
                  {!readOnly && (
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => onRemove(e.sf_id)}
                        aria-label={`Remove ${e.name} from roster`}
                        title="Remove from roster"
                        className="rounded p-1 text-muted-foreground hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40"
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
  const [pendingAddId, setPendingAddId] = useState<string | null>(null);

  const { data: entries = [], isLoading } = useQuery<RosterEntry[]>({
    queryKey: ["roster"],
    queryFn: fetchRoster,
    staleTime: 60_000,
  });

  const invalidate = (): void => {
    void qc.invalidateQueries({ queryKey: ["roster"] });
    void qc.invalidateQueries({ queryKey: ["filters"] });
  };

  const importMut = useMutation({
    mutationFn: importFromSf,
    onSuccess: (res) => {
      invalidate();
      toast.success(
        `Imported ${res.imported} AE${res.imported === 1 ? "" : "s"} from Salesforce`,
      );
    },
    onError: (err) => toast.error(`Import failed: ${(err as Error).message}`),
  });

  const addMut = useMutation({
    mutationFn: addToRoster,
    onMutate: (sfId: string) => {
      setPendingAddId(sfId);
    },
    onSuccess: (entry) => {
      invalidate();
      toast.success(`Added ${entry.name} to roster`);
    },
    onError: (err) => toast.error(`Add failed: ${(err as Error).message}`),
    onSettled: () => setPendingAddId(null),
  });

  const removeMut = useMutation({
    mutationFn: removeFromRoster,
    onSuccess: (_, sfId) => {
      const name = entries.find((e) => e.sf_id === sfId)?.name ?? "AE";
      invalidate();
      toast.success(`Removed ${name} from roster`);
    },
    onError: (err) => toast.error(`Remove failed: ${(err as Error).message}`),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold">AE Roster</h2>
          <p className="text-xs text-muted-foreground">
            {entries.length} AE{entries.length !== 1 ? "s" : ""} · Manager and
            SDR shown for visibility only
          </p>
        </div>
        {!readOnly && (
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => importMut.mutate()}
              disabled={importMut.isPending}
              className="flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <Download
                className={cn(
                  "h-4 w-4",
                  importMut.isPending && "animate-pulse",
                )}
              />
              {importMut.isPending ? "Importing…" : "Import from Salesforce"}
            </button>
            <AddAEDialog
              alreadyAdded={new Set(entries.map((e) => e.sf_id))}
              onAdd={(id) => addMut.mutate(id)}
              isAdding={addMut.isPending}
              pendingId={pendingAddId}
            />
          </div>
        )}
      </div>

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
