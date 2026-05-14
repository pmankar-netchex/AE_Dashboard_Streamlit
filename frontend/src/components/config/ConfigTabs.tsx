import { Link, useRouterState } from "@tanstack/react-router";
import { cn } from "@/lib/cn";

const TABS = [
  { to: "/config/soql", label: "SOQL Management" },
  { to: "/config/salesforce", label: "Salesforce Connection" },
  { to: "/config/users", label: "User Management" },
] as const;

export function ConfigTabs() {
  const { location } = useRouterState();
  return (
    <nav className="border-b border-border">
      <div className="-mb-px flex gap-1">
        {TABS.map((t) => {
          const active = location.pathname.startsWith(t.to);
          return (
            <Link
              key={t.to}
              to={t.to}
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
