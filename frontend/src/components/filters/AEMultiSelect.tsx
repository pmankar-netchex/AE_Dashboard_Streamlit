import * as Popover from "@radix-ui/react-popover";
import { Check, ChevronDown, X } from "lucide-react";
import { useAes } from "@/hooks/useDashboard";
import { useFilters } from "@/hooks/useFilters";
import { cn } from "@/lib/cn";

export function AEMultiSelect() {
  const { filters, set } = useFilters();
  const { data, isLoading } = useAes(filters.manager);
  const aes = data ?? [];
  const selectedSet = new Set(filters.aeIds);
  const toggle = (id: string): void => {
    const next = selectedSet.has(id)
      ? filters.aeIds.filter((x) => x !== id)
      : [...filters.aeIds, id];
    set({ aeIds: next });
  };
  const labelText =
    filters.aeIds.length === 0
      ? "All AEs"
      : filters.aeIds.length === 1
        ? (aes.find((a) => a.id === filters.aeIds[0])?.name ?? `1 AE`)
        : `${filters.aeIds.length} AEs`;

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">AE</span>
      <Popover.Root>
        <Popover.Trigger asChild>
          <button
            type="button"
            disabled={isLoading}
            className="flex h-8 min-w-[12rem] items-center justify-between gap-2 rounded-md border border-border bg-background px-2 text-sm"
          >
            <span className="truncate">{labelText}</span>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            sideOffset={4}
            className="z-50 max-h-72 w-80 overflow-auto rounded-md border border-border bg-background p-1 shadow-lg"
          >
            <div className="flex items-center justify-between px-2 py-1 text-xs text-muted-foreground">
              <span>{aes.length} active AE(s)</span>
              {filters.aeIds.length > 0 && (
                <button
                  type="button"
                  onClick={() => set({ aeIds: [] })}
                  className="inline-flex items-center gap-1 hover:text-foreground"
                >
                  <X className="h-3 w-3" /> clear
                </button>
              )}
            </div>
            {aes.map((ae) => {
              const checked = selectedSet.has(ae.id);
              return (
                <button
                  type="button"
                  key={ae.id}
                  onClick={() => toggle(ae.id)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-accent",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 items-center justify-center rounded border",
                      checked
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border",
                    )}
                  >
                    {checked && <Check className="h-3 w-3" />}
                  </span>
                  <span className="truncate">{ae.name}</span>
                </button>
              );
            })}
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
