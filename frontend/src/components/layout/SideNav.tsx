import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, BarChart3, Mail, Settings } from "lucide-react";
import { cn } from "@/lib/cn";

const NAV = [
  { to: "/dashboard", label: "Dashboard", Icon: BarChart3 },
  { to: "/schedules", label: "Reports", Icon: Mail },
  { to: "/config", label: "Config", Icon: Settings },
  { to: "/audit", label: "Activity", Icon: Activity },
] as const;

export function SideNav() {
  const { location } = useRouterState();
  return (
    <aside className="flex w-56 flex-col border-r border-border bg-muted/30">
      <div className="flex h-14 items-center px-4 text-sm font-semibold">
        AE Dashboard
      </div>
      <nav className="flex-1 px-2 py-2">
        {NAV.map(({ to, label, Icon }) => {
          const active =
            location.pathname === to ||
            location.pathname.startsWith(to + "/");
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                "mb-1 flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
