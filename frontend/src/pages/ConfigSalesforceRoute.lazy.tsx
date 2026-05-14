import { createLazyRoute } from "@tanstack/react-router";
import { ConfigSalesforceRoute } from "./ConfigSalesforceRoute";

export const Route = createLazyRoute("/config/salesforce")({
  component: ConfigSalesforceRoute,
});
