import { createLazyRoute } from "@tanstack/react-router";
import { ConfigUsersRoute } from "./ConfigUsersRoute";

export const Route = createLazyRoute("/config/users")({
  component: ConfigUsersRoute,
});
