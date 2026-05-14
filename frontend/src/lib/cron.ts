/**
 * Friendly schedule builder.
 *
 * Maps a small UI-driven shape to a standard 5-field crontab string
 * (minute hour day-of-month month day-of-week). Round-trips: any cron
 * produced by makeCron() parses back to the same FriendlySchedule via
 * parseCron(). Anything else falls into "custom" so we don't lose
 * fidelity for power users.
 */

export type Frequency =
  | "daily"
  | "weekdays"
  | "weekly"
  | "monthly"
  | "custom";

export interface FriendlySchedule {
  frequency: Frequency;
  hour: number; // 0–23
  minute: number; // 0–59
  daysOfWeek: number[]; // 0=Sun … 6=Sat — used when frequency=weekly
  dayOfMonth: number; // 1–28 — used when frequency=monthly
  raw: string; // the actual cron string, source of truth in custom mode
}

export const DEFAULT_SCHEDULE: FriendlySchedule = {
  frequency: "daily",
  hour: 9,
  minute: 0,
  daysOfWeek: [1],
  dayOfMonth: 1,
  raw: "0 9 * * *",
};

export function makeCron(s: FriendlySchedule): string {
  const m = clamp(s.minute, 0, 59);
  const h = clamp(s.hour, 0, 23);
  switch (s.frequency) {
    case "daily":
      return `${m} ${h} * * *`;
    case "weekdays":
      return `${m} ${h} * * 1-5`;
    case "weekly": {
      const dows = (s.daysOfWeek.length ? s.daysOfWeek : [1])
        .slice()
        .sort()
        .join(",");
      return `${m} ${h} * * ${dows}`;
    }
    case "monthly":
      return `${m} ${h} ${clamp(s.dayOfMonth, 1, 28)} * *`;
    case "custom":
      return s.raw.trim();
  }
}

export function parseCron(raw: string): FriendlySchedule {
  const fallback: FriendlySchedule = { ...DEFAULT_SCHEDULE, raw, frequency: "custom" };
  const parts = raw.trim().split(/\s+/);
  if (parts.length !== 5) return fallback;
  const [min, hr, dom, mon, dow] = parts;
  const minute = parseSingleInt(min);
  const hour = parseSingleInt(hr);
  if (minute === null || hour === null) return fallback;
  if (mon !== "*") return fallback;

  // Daily
  if (dom === "*" && dow === "*") {
    return {
      frequency: "daily",
      hour,
      minute,
      daysOfWeek: [],
      dayOfMonth: 1,
      raw,
    };
  }
  // Weekdays (Mon-Fri)
  if (dom === "*" && (dow === "1-5" || dow === "MON-FRI")) {
    return {
      frequency: "weekdays",
      hour,
      minute,
      daysOfWeek: [1, 2, 3, 4, 5],
      dayOfMonth: 1,
      raw,
    };
  }
  // Weekly (specific days)
  if (dom === "*" && /^[0-6](,[0-6])*$/.test(dow)) {
    return {
      frequency: "weekly",
      hour,
      minute,
      daysOfWeek: dow.split(",").map((d) => parseInt(d, 10)),
      dayOfMonth: 1,
      raw,
    };
  }
  // Monthly
  if (dow === "*" && /^[1-9]\d?$/.test(dom)) {
    const n = parseInt(dom, 10);
    if (n >= 1 && n <= 28) {
      return {
        frequency: "monthly",
        hour,
        minute,
        daysOfWeek: [],
        dayOfMonth: n,
        raw,
      };
    }
  }
  return fallback;
}

/**
 * Human-readable summary of the schedule, e.g.
 *   "Daily at 9:00 AM (America/Chicago)"
 *   "Weekdays at 8:30 AM (America/Chicago)"
 *   "Mondays, Wednesdays at 5:00 PM (America/Chicago)"
 *   "Monthly on the 1st at 9:00 AM (America/Chicago)"
 */
export function describeSchedule(s: FriendlySchedule, tz: string): string {
  if (s.frequency === "custom") return `Custom (${s.raw}) — ${tz}`;
  const time = formatTime(s.hour, s.minute);
  const tzSuffix = tz ? ` (${tz})` : "";
  switch (s.frequency) {
    case "daily":
      return `Daily at ${time}${tzSuffix}`;
    case "weekdays":
      return `Weekdays at ${time}${tzSuffix}`;
    case "weekly": {
      const names = s.daysOfWeek.length ? s.daysOfWeek.map(dowName).join(", ") : "Monday";
      return `${names} at ${time}${tzSuffix}`;
    }
    case "monthly":
      return `Monthly on the ${ordinal(s.dayOfMonth)} at ${time}${tzSuffix}`;
  }
}

export const DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function dowName(n: number): string {
  const names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  return names[clamp(n, 0, 6)];
}

function ordinal(n: number): string {
  const j = n % 10;
  const k = n % 100;
  if (k >= 11 && k <= 13) return `${n}th`;
  if (j === 1) return `${n}st`;
  if (j === 2) return `${n}nd`;
  if (j === 3) return `${n}rd`;
  return `${n}th`;
}

function formatTime(h: number, m: number): string {
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${period}`;
}

function parseSingleInt(s: string): number | null {
  if (!/^\d+$/.test(s)) return null;
  const n = parseInt(s, 10);
  return Number.isFinite(n) ? n : null;
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, n));
}
