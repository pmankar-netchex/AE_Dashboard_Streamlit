import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/cn";

export function RefreshButton() {
  const qc = useQueryClient();
  const isFetching = qc.isFetching({ queryKey: ["dashboard"] }) > 0;
  return (
    <button
      type="button"
      onClick={() => {
        void qc.invalidateQueries({ queryKey: ["dashboard"] });
        void qc.invalidateQueries({ queryKey: ["ae-detail"] });
      }}
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-xs hover:bg-accent"
    >
      <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
      Refresh
    </button>
  );
}
