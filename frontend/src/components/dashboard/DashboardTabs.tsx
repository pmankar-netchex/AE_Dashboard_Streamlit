import { Link, useRouterState } from "@tanstack/react-router";
import { cn } from "@/lib/cn";

const TABS = [
  { to: "/dashboard/summary", label: "Summary" },
  { to: "/dashboard/charts", label: "Charts" },
  { to: "/dashboard/heatmap", label: "Performance Heatmap" },
] as const;

export function DashboardTabs() {
  const { location } = useRouterState();
  return (
    <nav className="border-b border-border">
      <div className="-mb-px flex gap-1">
        {TABS.map((t) => {
          const active =
            location.pathname === t.to ||
            location.pathname === t.to + "/";
          return (
            <Link
              key={t.to}
              to={t.to}
              search={(prev) => prev}
              className={cn(
                "border-b-2 px-3 py-2 text-sm",
                active
                  ? "border-primary font-medium text-foreground"
                  : "border-transparent text-muted-foreground hover:border-border hover:text-foreground",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
