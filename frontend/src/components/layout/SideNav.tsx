import * as Tooltip from "@radix-ui/react-tooltip";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  type LucideIcon,
  Mail,
  Settings,
} from "lucide-react";
import { Logo } from "./Logo";
import { UserMenu } from "./UserMenu";
import { useUiStore } from "@/stores/uiStore";
import { SECTION_DEFS } from "@/lib/sections";
import { cn } from "@/lib/cn";

interface Entry {
  to: string;
  label: string;
}

interface TopEntry extends Entry {
  Icon: LucideIcon;
  subnav?: Entry[];
}

const DASHBOARD_SUBNAV: Entry[] = [
  { to: "/dashboard/summary", label: "Summary" },
  ...SECTION_DEFS.map((s) => ({
    to: `/dashboard/section/${s.slug}`,
    label: s.label,
  })),
  { to: "/dashboard/charts", label: "Charts" },
  { to: "/dashboard/heatmap", label: "Heatmap" },
];

const CONFIG_SUBNAV: Entry[] = [
  { to: "/config/soql", label: "SOQL Management" },
  { to: "/config/salesforce", label: "Salesforce Connection" },
  { to: "/config/users", label: "User Management" },
  { to: "/config/roster", label: "AE Roster" },
];

// "Operations" group — what users do day-to-day.
const PRIMARY_NAV: TopEntry[] = [
  {
    to: "/dashboard",
    label: "Dashboard",
    Icon: LayoutDashboard,
    subnav: DASHBOARD_SUBNAV,
  },
  { to: "/schedules", label: "Reports", Icon: Mail },
];

// "Governance" group — admin / audit. Visually separated below.
const ADMIN_NAV: TopEntry[] = [
  { to: "/config", label: "Config", Icon: Settings, subnav: CONFIG_SUBNAV },
  { to: "/audit", label: "Activity", Icon: Activity },
];

export function SideNav() {
  const { location } = useRouterState();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggle = useUiStore((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-border bg-muted/30 transition-[width] duration-150",
        collapsed ? "w-14" : "w-60",
      )}
      style={{ width: collapsed ? 56 : 240 }}
    >
      {/* Header — logo only; chevron lives in the footer now */}
      <div
        className={cn(
          "flex h-14 shrink-0 items-center overflow-hidden border-b border-border/60",
          collapsed ? "justify-center px-2" : "px-3",
        )}
      >
        <Logo iconOnly={collapsed} size={28} className="min-w-0 flex-1" />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <NavGroup nav={PRIMARY_NAV} collapsed={collapsed} pathname={location.pathname} />
        <div className="my-2 mx-1 border-t border-border/60" />
        <NavGroup nav={ADMIN_NAV} collapsed={collapsed} pathname={location.pathname} />
      </nav>

      {/* Footer — user identity + collapse toggle */}
      <div className="shrink-0 border-t border-border/60 px-2 py-2">
        <UserMenu collapsed={collapsed} />
        <button
          type="button"
          onClick={toggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={cn(
            "mt-1 flex w-full items-center gap-2 rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:bg-accent hover:text-foreground",
            collapsed && "justify-center",
          )}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-3.5 w-3.5" />
              <span>Collapse sidebar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}

function NavGroup({
  nav,
  collapsed,
  pathname,
}: {
  nav: TopEntry[];
  collapsed: boolean;
  pathname: string;
}) {
  return (
    <ul className="space-y-0.5">
      {nav.map((entry) => (
        <TopEntryItem
          key={entry.to}
          entry={entry}
          collapsed={collapsed}
          pathname={pathname}
        />
      ))}
    </ul>
  );
}

function TopEntryItem({
  entry,
  collapsed,
  pathname,
}: {
  entry: TopEntry;
  collapsed: boolean;
  pathname: string;
}) {
  const { Icon, to, label, subnav } = entry;
  const isOnRoute = pathname === to || pathname.startsWith(to + "/");
  // Active sub-item label (used in collapsed tooltip)
  const activeSub = subnav?.find((s) => pathname.startsWith(s.to));
  const childActive = !!activeSub;
  const expandSubnav = !collapsed && isOnRoute && subnav && subnav.length > 0;

  const topClass = childActive
    ? // Parent demotes to a section-header look when a child is selected.
      "flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm font-semibold text-foreground hover:bg-accent/60 transition-colors"
    : isOnRoute
      ? "flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm font-medium bg-accent text-foreground"
      : "flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors";

  const collapsedClass = cn(
    "flex h-9 w-9 items-center justify-center rounded-md",
    isOnRoute
      ? "bg-accent text-foreground"
      : "text-muted-foreground hover:bg-accent hover:text-foreground transition-colors",
  );

  const linkEl = collapsed ? (
    <Tooltip.Root delayDuration={120}>
      <Tooltip.Trigger asChild>
        <Link to={to} search={(prev) => prev} className={collapsedClass}>
          <Icon className="h-4 w-4 shrink-0" />
        </Link>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="right"
          sideOffset={8}
          className="z-50 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
        >
          <span className="font-medium text-foreground">{label}</span>
          {activeSub && (
            <span className="ml-1.5 text-muted-foreground">
              › {activeSub.label}
            </span>
          )}
          <Tooltip.Arrow className="fill-background" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  ) : (
    <Link to={to} search={(prev) => prev} className={topClass}>
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
    </Link>
  );

  return (
    <li>
      {collapsed ? (
        <div className="flex justify-center py-0.5">{linkEl}</div>
      ) : (
        linkEl
      )}

      {expandSubnav && (
        // Left rail aligns with parent icon centerline.
        <ul className="my-0.5 ml-[1.375rem] flex flex-col gap-px border-l border-border/60 pl-2">
          {subnav!.map((sub) => {
            const subActive = pathname.startsWith(sub.to);
            return (
              <li key={sub.to}>
                <Link
                  to={sub.to}
                  search={(prev) => prev}
                  data-active={subActive ? "true" : undefined}
                  className={cn(
                    "group flex items-center gap-2 rounded-md px-2 py-1 text-[13px] transition-colors",
                    subActive
                      ? "bg-accent font-medium text-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "size-1 shrink-0 rounded-full transition-opacity",
                      subActive
                        ? "bg-foreground/60 opacity-100"
                        : "bg-muted-foreground/0 opacity-0",
                    )}
                  />
                  <span className="truncate">{sub.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </li>
  );
}
