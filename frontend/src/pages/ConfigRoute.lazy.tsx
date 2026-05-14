import { createLazyRoute } from "@tanstack/react-router";
import { ConfigRoute } from "./ConfigRoute";

export const Route = createLazyRoute("/config")({
  component: ConfigRoute,
});
