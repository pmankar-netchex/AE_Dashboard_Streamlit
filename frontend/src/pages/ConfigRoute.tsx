import { Outlet } from "@tanstack/react-router";
import { ConfigTabs } from "@/components/config/ConfigTabs";

export function ConfigRoute() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Config</h1>
        <p className="text-sm text-muted-foreground">
          SOQL queries, Salesforce connection, and user roles. Admin role can
          edit; user role is view-only.
        </p>
      </header>
      <ConfigTabs />
      <Outlet />
    </div>
  );
}
