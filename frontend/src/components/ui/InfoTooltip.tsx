import * as Tooltip from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

interface Props {
  title: string;
  description?: string;
  children: ReactNode;
  /** Side to open on (default top). */
  side?: "top" | "right" | "bottom" | "left";
}

/**
 * Hover/focus tooltip with a bold title and an optional muted description.
 * One TooltipProvider sits at the app root in App.tsx; this component is
 * the leaf that wraps the trigger.
 */
export function InfoTooltip({ title, description, children, side = "top" }: Props) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <span className="inline-flex">{children}</span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side={side}
          sideOffset={4}
          collisionPadding={8}
          className="z-50 max-w-xs rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
        >
          <div className="font-medium text-foreground">{title}</div>
          {description && (
            <div className="mt-1 leading-snug text-muted-foreground">
              {description}
            </div>
          )}
          <Tooltip.Arrow className="fill-background" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
