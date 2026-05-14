import { createLazyRoute } from "@tanstack/react-router";
import { AuditRoute } from "./AuditRoute";

export const Route = createLazyRoute("/audit")({
  component: AuditRoute,
});
