import { useFilters } from "@/hooks/useFilters";
import { useManagers } from "@/hooks/useDashboard";

export function ManagerSelect() {
  const { filters, set } = useFilters();
  const { data, isLoading } = useManagers();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">Manager</span>
      <select
        className="h-8 rounded-md border border-border bg-background px-2 text-sm"
        value={filters.manager ?? ""}
        disabled={isLoading}
        onChange={(e) => set({ manager: e.target.value || null, aeIds: [] })}
      >
        <option value="">All Managers</option>
        {(data ?? []).map((m) => (
          <option key={m.name} value={m.name}>
            {m.name}
          </option>
        ))}
      </select>
    </label>
  );
}
