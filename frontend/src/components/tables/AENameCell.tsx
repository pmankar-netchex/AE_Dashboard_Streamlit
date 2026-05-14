import { useFilters } from "@/hooks/useFilters";
import { cn } from "@/lib/cn";

interface Props {
  aeId: string;
  name: string;
  className?: string;
}

export function AENameCell({ aeId, name, className }: Props) {
  const { set } = useFilters();
  return (
    <td className={cn("sticky left-0 z-10 bg-background px-2 py-1.5 text-sm", className)}>
      <button
        type="button"
        className="text-left font-medium text-foreground hover:underline"
        onClick={() => set({ aeDrillId: aeId })}
      >
        {name}
      </button>
    </td>
  );
}
