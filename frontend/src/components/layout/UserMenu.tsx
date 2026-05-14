import * as Popover from "@radix-ui/react-popover";
import * as Tooltip from "@radix-ui/react-tooltip";
import { LogOut } from "lucide-react";
import { useMe } from "@/hooks/useMe";
import { cn } from "@/lib/cn";

function initials(email: string | undefined): string {
  if (!email) return "?";
  const local = email.split("@")[0] ?? "";
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return (local.slice(0, 2) || "?").toUpperCase();
}

export function UserMenu({ collapsed }: { collapsed: boolean }) {
  const { data: me } = useMe();
  const email = me?.email ?? "";
  const role = me?.role ?? "user";
  const ini = initials(email);

  const avatar = (
    <span
      className={cn(
        "inline-flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full border border-border bg-muted text-[11px] font-medium text-foreground",
      )}
    >
      {ini}
    </span>
  );

  if (collapsed) {
    return (
      <Tooltip.Root delayDuration={150}>
        <Tooltip.Trigger asChild>
          <a
            href="/.auth/logout"
            aria-label={email ? `Signed in as ${email}. Sign out.` : "Sign out"}
            className="flex justify-center py-1"
          >
            {avatar}
          </a>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side="right"
            sideOffset={8}
            className="z-50 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
          >
            <div className="font-medium">{email || "Signed in"}</div>
            <div className="mt-0.5 text-muted-foreground">
              {role} • click to sign out
            </div>
            <Tooltip.Arrow className="fill-background" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    );
  }

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-accent"
        >
          {avatar}
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-xs font-medium text-foreground">
              {email || "Signed in"}
            </span>
            <span className="block text-[10px] uppercase tracking-wide text-muted-foreground">
              {role}
            </span>
          </span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          side="top"
          align="start"
          sideOffset={6}
          className="z-50 w-56 rounded-md border border-border bg-background p-1 shadow-lg"
        >
          <div className="px-2 py-1.5 text-[11px] text-muted-foreground">
            Signed in as
            <div className="mt-0.5 break-all font-medium text-foreground">
              {email || "—"}
            </div>
          </div>
          <div className="my-1 h-px bg-border" />
          <a
            href="/.auth/logout"
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
          >
            <LogOut className="h-4 w-4 text-muted-foreground" />
            <span>Sign out</span>
          </a>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
