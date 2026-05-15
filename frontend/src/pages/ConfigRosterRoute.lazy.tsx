import { createLazyRoute } from "@tanstack/react-router";
import { ConfigRosterRoute } from "./ConfigRosterRoute";

export const Route = createLazyRoute("/config/roster")({
  component: ConfigRosterRoute,
});
