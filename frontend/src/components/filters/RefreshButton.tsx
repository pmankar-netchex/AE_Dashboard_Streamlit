import * as Tooltip from "@radix-ui/react-tooltip";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/cn";

export function RefreshButton({ iconOnly = false }: { iconOnly?: boolean }) {
  const qc = useQueryClient();
  const isFetching = qc.isFetching({ queryKey: ["dashboard"] }) > 0;

  const button = (
    <button
      type="button"
      onClick={() => {
        void qc.invalidateQueries({ queryKey: ["dashboard"] });
        void qc.invalidateQueries({ queryKey: ["ae-detail"] });
      }}
      aria-label="Refresh dashboard data"
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background text-xs text-foreground hover:bg-accent",
        iconOnly ? "w-8 justify-center" : "px-2.5",
      )}
    >
      <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
      {!iconOnly && <span>Refresh</span>}
    </button>
  );

  if (!iconOnly) return button;
  return (
    <Tooltip.Root delayDuration={150}>
      <Tooltip.Trigger asChild>{button}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="bottom"
          sideOffset={6}
          className="z-50 rounded-md border border-border bg-background px-2 py-1 text-[11px] shadow-md"
        >
          {isFetching ? "Refreshing…" : "Refresh data"}
          <Tooltip.Arrow className="fill-background" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
