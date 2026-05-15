import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  type Role,
  type UserRow,
  createUser,
  deleteUser,
  listUsers,
  updateUser,
} from "@/api/users";
import { useReadOnly } from "@/components/auth/ReadOnlyGate";
import { useMe } from "@/hooks/useMe";
import { formatInTz, useTz } from "@/lib/datetime";
import { cn } from "@/lib/cn";

export function UserList() {
  const readOnly = useReadOnly();
  const tz = useTz();
  const { data: me } = useMe();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<UserRow[]>({
    queryKey: ["users"],
    queryFn: listUsers,
  });

  const [adding, setAdding] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState<Role>("user");

  const invalidate = (): void => {
    void qc.invalidateQueries({ queryKey: ["users"] });
  };

  const createMut = useMutation({
    mutationFn: () =>
      createUser({ email: newEmail.trim().toLowerCase(), role: newRole, is_active: true }),
    onSuccess: (u) => {
      setAdding(false);
      setNewEmail("");
      setNewRole("user");
      invalidate();
      toast.success(`Added ${u.email}`);
    },
    onError: (err) => toast.error(`Add failed: ${(err as Error).message}`),
  });

  const updateMut = useMutation({
    mutationFn: ({ email, body }: { email: string; body: { role?: Role; is_active?: boolean } }) =>
      updateUser(email, body),
    onSuccess: (_, { email, body }) => {
      invalidate();
      if (body.role) toast.success(`Set ${email} to ${body.role}`);
      else if (body.is_active !== undefined)
        toast.success(`${body.is_active ? "Enabled" : "Disabled"} ${email}`);
      else toast.success(`Updated ${email}`);
    },
    onError: (err) => toast.error(`Update failed: ${(err as Error).message}`),
  });

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: (_, email) => {
      invalidate();
      toast.success(`Removed ${email}`);
    },
    onError: (err) => toast.error(`Remove failed: ${(err as Error).message}`),
  });

  return (
    <div className="space-y-3">
      <header className="flex items-center justify-between">
        <h3 className="text-base font-semibold">Users</h3>
        {!readOnly && (
          <button
            type="button"
            onClick={() => setAdding((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm hover:bg-accent"
          >
            <Plus className="h-3.5 w-3.5" /> Add user
          </button>
        )}
      </header>

      {adding && !readOnly && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMut.mutate();
          }}
          className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-muted/30 p-3"
        >
          <input
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="email@example.com"
            required
            className="h-8 flex-1 rounded-md border border-border bg-background px-2 text-sm"
          />
          <select
            value={newRole}
            onChange={(e) => setNewRole(e.target.value as Role)}
            className="h-8 rounded-md border border-border bg-background px-2 text-sm"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
          <button
            type="submit"
            disabled={createMut.isPending}
            className="h-8 rounded-md bg-primary px-3 text-sm text-primary-foreground hover:bg-primary/90"
          >
            {createMut.isPending ? "…" : "Add"}
          </button>
          <button
            type="button"
            onClick={() => setAdding(false)}
            className="h-8 rounded-md border border-border bg-background px-3 text-sm hover:bg-accent"
          >
            Cancel
          </button>
          {createMut.isError && (
            <span className="text-xs text-red-700">
              {(createMut.error as Error).message}
            </span>
          )}
        </form>
      )}

      <div className="overflow-hidden rounded-md border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50 text-xs">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Email</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Role</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Status</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Added</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  Loading…
                </td>
              </tr>
            )}
            {data?.length === 0 && !isLoading && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  No users yet.
                </td>
              </tr>
            )}
            {data?.map((u) => {
              const isSelf = me?.email.toLowerCase() === u.email.toLowerCase();
              return (
                <tr key={u.email} className="border-t border-border">
                  <td className="px-3 py-2 font-mono text-xs">{u.email}</td>
                  <td className="px-3 py-2">
                    <select
                      disabled={readOnly || isSelf}
                      value={u.role}
                      onChange={(e) =>
                        updateMut.mutate({
                          email: u.email,
                          body: { role: e.target.value as Role },
                        })
                      }
                      className="h-7 rounded border border-border bg-background px-1 text-xs disabled:opacity-50"
                    >
                      <option value="user">user</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      disabled={readOnly || isSelf}
                      onClick={() =>
                        updateMut.mutate({
                          email: u.email,
                          body: { is_active: !u.is_active },
                        })
                      }
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs",
                        u.is_active
                          ? "bg-green-100 text-green-900"
                          : "bg-muted text-muted-foreground",
                        (readOnly || isSelf) && "opacity-50",
                      )}
                    >
                      {u.is_active ? "active" : "disabled"}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">
                    {formatInTz(u.added_at, tz, { dateOnly: true })}
                    {u.added_by ? ` • ${u.added_by}` : ""}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {!readOnly && !isSelf && (
                      <button
                        type="button"
                        onClick={() => {
                          if (confirm(`Remove ${u.email}?`)) {
                            deleteMut.mutate(u.email);
                          }
                        }}
                        className="text-muted-foreground hover:text-red-700"
                        aria-label="Delete user"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
