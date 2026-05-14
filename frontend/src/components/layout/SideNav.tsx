import { Link, useRouterState } from "@tanstack/react-router";
import {
  Activity,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FileBarChart,
  Flame,
  LayoutDashboard,
  type LucideIcon,
  Mail,
  Megaphone,
  Settings,
  Target,
  Users2,
  Zap,
} from "lucide-react";
import { Logo } from "./Logo";
import { useUiStore } from "@/stores/uiStore";
import { SECTION_DEFS } from "@/lib/sections";
import { cn } from "@/lib/cn";

interface Entry {
  to: string;
  label: string;
  Icon: LucideIcon;
}

const TOP_NAV: Entry[] = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { to: "/schedules", label: "Reports", Icon: Mail },
  { to: "/config", label: "Config", Icon: Settings },
  { to: "/audit", label: "Activity", Icon: Activity },
];

const SECTION_ICONS: Record<string, LucideIcon> = {
  "pipeline-quota": Target,
  "self-gen": Zap,
  sdr: Users2,
  channel: Users2,
  marketing: Megaphone,
};

const DASHBOARD_SUBNAV: Entry[] = [
  { to: "/dashboard/summary", label: "Summary", Icon: BarChart3 },
  ...SECTION_DEFS.map((s) => ({
    to: `/dashboard/section/${s.slug}`,
    label: s.label,
    Icon: SECTION_ICONS[s.slug] ?? BarChart3,
  })),
  { to: "/dashboard/charts", label: "Charts", Icon: FileBarChart },
  { to: "/dashboard/heatmap", label: "Heatmap", Icon: Flame },
];

export function SideNav() {
  const { location } = useRouterState();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggle = useUiStore((s) => s.toggleSidebar);

  const dashboardActive = location.pathname.startsWith("/dashboard");

  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-border bg-muted/30 transition-[width] duration-150",
        collapsed ? "w-14" : "w-60",
      )}
      style={{ width: collapsed ? 56 : 240 }}
    >
      <div
        className={cn(
          "flex h-14 shrink-0 items-center gap-2 border-b border-border/60 overflow-hidden",
          collapsed ? "justify-center px-2" : "justify-between px-3",
        )}
      >
        <Logo iconOnly={collapsed} size={28} className="min-w-0 flex-1" />
        {!collapsed && (
          <button
            type="button"
            onClick={toggle}
            aria-label="Collapse sidebar"
            className="shrink-0 rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        )}
      </div>
      {collapsed && (
        <button
          type="button"
          onClick={toggle}
          aria-label="Expand sidebar"
          className="mt-1 self-center rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      )}
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {TOP_NAV.map(({ to, label, Icon }) => {
          const active =
            location.pathname === to || location.pathname.startsWith(to + "/");
          return (
            <div key={to} className="mb-0.5">
              <NavLink
                to={to}
                label={label}
                Icon={Icon}
                active={active}
                collapsed={collapsed}
              />
              {!collapsed && to === "/dashboard" && dashboardActive && (
                <ul className="my-1 ml-3 space-y-0.5 border-l border-border/50 pl-2">
                  {DASHBOARD_SUBNAV.map((sub) => {
                    const subActive = location.pathname.startsWith(sub.to);
                    return (
                      <li key={sub.to}>
                        <Link
                          to={sub.to}
                          search={(prev) => prev}
                          className={cn(
                            "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs",
                            subActive
                              ? "bg-accent font-medium text-foreground"
                              : "text-muted-foreground hover:bg-accent hover:text-foreground",
                          )}
                        >
                          <sub.Icon className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">{sub.label}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}

function NavLink({
  to,
  label,
  Icon,
  active,
  collapsed,
}: {
  to: string;
  label: string;
  Icon: LucideIcon;
  active: boolean;
  collapsed: boolean;
}) {
  return (
    <Link
      to={to}
      search={(prev) => prev}
      title={collapsed ? label : undefined}
      className={cn(
        "flex items-center gap-2 rounded-md text-sm",
        collapsed ? "justify-center px-1.5 py-2" : "px-3 py-2",
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-foreground",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );
}
