import { createLazyRoute } from "@tanstack/react-router";
import { ConfigSoqlRoute } from "./ConfigSoqlRoute";

export const Route = createLazyRoute("/config/soql")({
  component: ConfigSoqlRoute,
});
