import {
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { AuditRoute } from "@/pages/AuditRoute";
import { ConfigRoute } from "@/pages/ConfigRoute";
import { DashboardRoute } from "@/pages/DashboardRoute";
import { SchedulesRoute } from "@/pages/SchedulesRoute";

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
});

const schedulesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/schedules",
  component: SchedulesRoute,
});

const configRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/config",
  component: ConfigRoute,
});

const auditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/audit",
  component: AuditRoute,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  dashboardRoute,
  schedulesRoute,
  configRoute,
  auditRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
