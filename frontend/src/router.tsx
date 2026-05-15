import {
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { DashboardRoute } from "@/pages/DashboardRoute";
import { DashboardChartsRoute } from "@/pages/DashboardChartsRoute";
import { DashboardHeatmapRoute } from "@/pages/DashboardHeatmapRoute";
import { DashboardSectionRoute } from "@/pages/DashboardSectionRoute";
import { DashboardSummaryRoute } from "@/pages/DashboardSummaryRoute";
import type { FilterSearch } from "@/lib/filterParams";

const rootRoute = createRootRoute({
  component: AppShell,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/dashboard" });
  },
});

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/dashboard",
  component: DashboardRoute,
  validateSearch: (raw: Record<string, unknown>): FilterSearch => ({
    manager: typeof raw.manager === "string" ? raw.manager : undefined,
    ae: Array.isArray(raw.ae)
      ? (raw.ae as string[])
      : typeof raw.ae === "string"
        ? [raw.ae as string]
        : undefined,
    period: typeof raw.period === "string" ? raw.period : undefined,
    from: typeof raw.from === "string" ? raw.from : undefined,
    to: typeof raw.to === "string" ? raw.to : undefined,
    aeDrillId: typeof raw.aeDrillId === "string" ? raw.aeDrillId : undefined,
  }),
});

const dashboardIndexRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/dashboard/summary" });
  },
});

const dashboardSummaryRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: "summary",
  component: DashboardSummaryRoute,
});

const dashboardChartsRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: "charts",
  component: DashboardChartsRoute,
});

const dashboardHeatmapRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: "heatmap",
  component: DashboardHeatmapRoute,
});

const dashboardSectionRoute = createRoute({
  getParentRoute: () => dashboardRoute,
  path: "section/$slug",
  component: DashboardSectionRoute,
});

const schedulesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/schedules",
}).lazy(() => import("@/pages/SchedulesRoute.lazy").then((m) => m.Route));

const configRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/config",
}).lazy(() => import("@/pages/ConfigRoute.lazy").then((m) => m.Route));

const configIndexRoute = createRoute({
  getParentRoute: () => configRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/config/soql" });
  },
});

const configSoqlRoute = createRoute({
  getParentRoute: () => configRoute,
  path: "soql",
}).lazy(() => import("@/pages/ConfigSoqlRoute.lazy").then((m) => m.Route));

const configSalesforceRoute = createRoute({
  getParentRoute: () => configRoute,
  path: "salesforce",
}).lazy(() =>
  import("@/pages/ConfigSalesforceRoute.lazy").then((m) => m.Route),
);

const configUsersRoute = createRoute({
  getParentRoute: () => configRoute,
  path: "users",
}).lazy(() => import("@/pages/ConfigUsersRoute.lazy").then((m) => m.Route));

const configRosterRoute = createRoute({
  getParentRoute: () => configRoute,
  path: "roster",
}).lazy(() => import("@/pages/ConfigRosterRoute.lazy").then((m) => m.Route));

const auditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/audit",
}).lazy(() => import("@/pages/AuditRoute.lazy").then((m) => m.Route));

const routeTree = rootRoute.addChildren([
  indexRoute,
  dashboardRoute.addChildren([
    dashboardIndexRoute,
    dashboardSummaryRoute,
    dashboardChartsRoute,
    dashboardHeatmapRoute,
    dashboardSectionRoute,
  ]),
  schedulesRoute,
  configRoute.addChildren([
    configIndexRoute,
    configSoqlRoute,
    configSalesforceRoute,
    configUsersRoute,
    configRosterRoute,
  ]),
  auditRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
