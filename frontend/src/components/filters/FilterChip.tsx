import * as Popover from "@radix-ui/react-popover";
import { ChevronDown } from "lucide-react";
import { type ReactNode, useState } from "react";
import { cn } from "@/lib/cn";

interface Props {
  label: string;
  /** Shown after the label (e.g. "All managers", "3 selected"). */
  value: string;
  /** Mark the chip visually as "non-default" to surface applied filters. */
  active?: boolean;
  /** Popover body. Receives `close` so internal Apply/Done buttons can shut it. */
  children: (ctx: { close: () => void }) => ReactNode;
  /** Width of the popover content. */
  popoverWidthClass?: string;
}

/**
 * Pill-shaped filter trigger. Same shape for Manager / AE / Period — clicking
 * opens a Popover with the actual control inside. Consistent visual language
 * across the filter strip (Stripe / Linear-style).
 */
export function FilterChip({
  label,
  value,
  active = false,
  children,
  popoverWidthClass = "w-72",
}: Props) {
  const [open, setOpen] = useState(false);
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-colors",
            active
              ? "border-foreground/20 bg-accent text-foreground"
              : "border-border bg-background text-foreground hover:bg-accent",
            "aria-expanded:bg-accent",
          )}
        >
          <span className="text-muted-foreground">{label}:</span>
          <span className="max-w-[14rem] truncate">{value}</span>
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          align="start"
          className={cn(
            "z-50 rounded-md border border-border bg-background p-2 shadow-lg",
            popoverWidthClass,
          )}
        >
          {children({ close: () => setOpen(false) })}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
