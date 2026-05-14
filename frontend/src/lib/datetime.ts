import { useMe } from "@/hooks/useMe";

const DEFAULT_TZ = "America/Chicago";

/** Resolve the app-wide timezone (Central by default; configurable via SCHEDULER_TZ). */
export function useTz(): string {
  const { data: me } = useMe();
  return me?.flags.scheduler_tz ?? DEFAULT_TZ;
}

interface FormatOpts {
  /** Show seconds (default false). */
  seconds?: boolean;
  /** Show the timezone abbreviation (CT/CDT/...) (default true). */
  showTz?: boolean;
  /** Date-only output (no time). */
  dateOnly?: boolean;
}

/**
 * Format a backend timestamp in the app timezone (defaults to America/Chicago).
 *
 * Accepts ISO strings, epoch seconds, epoch ms, or Date objects. Returns "—"
 * for null / empty / unparseable input.
 *
 *   formatInTz("2026-05-14T16:35:15Z", "America/Chicago")
 *   → "May 14, 2026, 11:35 AM CDT"
 */
export function formatInTz(
  input: string | number | Date | null | undefined,
  tz: string,
  opts: FormatOpts = {},
): string {
  if (input == null || input === "") return "—";
  let date: Date;
  if (typeof input === "number") {
    // Heuristic: numbers < 1e12 are epoch seconds, otherwise ms
    date = new Date(input < 1e12 ? input * 1000 : input);
  } else if (input instanceof Date) {
    date = input;
  } else {
    date = new Date(input);
  }
  if (isNaN(date.getTime())) return "—";

  const options: Intl.DateTimeFormatOptions = {
    timeZone: tz,
    year: "numeric",
    month: "short",
    day: "2-digit",
  };
  if (!opts.dateOnly) {
    options.hour = "numeric";
    options.minute = "2-digit";
    options.hour12 = true;
    if (opts.seconds) options.second = "2-digit";
    if (opts.showTz !== false) options.timeZoneName = "short";
  }
  return new Intl.DateTimeFormat("en-US", options).format(date);
}

/** Short variant: "May 14, 11:35 AM" — no year, no tz suffix. */
export function formatShortInTz(
  input: string | number | Date | null | undefined,
  tz: string,
): string {
  if (input == null || input === "") return "—";
  const date =
    typeof input === "number"
      ? new Date(input < 1e12 ? input * 1000 : input)
      : input instanceof Date
        ? input
        : new Date(input);
  if (isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    month: "short",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}
