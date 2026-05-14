import { createLazyRoute } from "@tanstack/react-router";
import { SchedulesRoute } from "./SchedulesRoute";

export const Route = createLazyRoute("/schedules")({
  component: SchedulesRoute,
});
