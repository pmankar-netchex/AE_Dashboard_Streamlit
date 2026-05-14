import * as Tooltip from "@radix-ui/react-tooltip";
import type { AERow, ColumnMeta } from "@/types/dashboard";
import { rdylgnFor } from "@/lib/heatmap";
import { fmt } from "@/lib/formatters";
import { LOWER_IS_BETTER } from "@/lib/columns";

interface Props {
  rows: AERow[];
  columns: ColumnMeta[];
}

export function PerformanceHeatmap({ rows, columns }: Props) {
  const numericCols = columns.filter((c) => !c.blocked && !c.computed);
  const maxByCol: Record<string, number> = {};
  for (const c of numericCols) {
    let max = 0;
    for (const r of rows) {
      const v = r.values[c.col_id];
      if (v != null && Number.isFinite(v)) max = Math.max(max, Math.abs(v as number));
    }
    maxByCol[c.col_id] = max;
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-border p-6 text-sm text-muted-foreground">
        No data to render heatmap.
      </div>
    );
  }

  return (
    <section className="rounded-lg border border-border p-4">
      <header className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium">Performance Heatmap</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Per-column normalized. Hover a cell for the AE, column, and value.
          </p>
        </div>
        <Legend />
      </header>

      <div className="overflow-x-auto">
        <div
          className="grid gap-px bg-border"
          style={{
            gridTemplateColumns: `180px repeat(${numericCols.length}, minmax(72px, 1fr))`,
          }}
        >
          {/* Header row — horizontal labels with two-line abbreviation */}
          <div className="sticky left-0 z-10 flex h-14 items-end bg-background px-2 pb-2 text-xs font-medium text-muted-foreground">
            AE
          </div>
          {numericCols.map((c) => {
            const { primary, period } = makeShortLabel(c);
            return (
              <Tooltip.Root key={`h-${c.col_id}`}>
                <Tooltip.Trigger asChild>
                  <div className="flex h-14 cursor-help flex-col items-center justify-end gap-0.5 bg-background px-1 pb-1.5 leading-tight">
                    <span className="line-clamp-2 break-words text-center text-[10px] font-medium text-foreground">
                      {primary}
                    </span>
                    {period && (
                      <span className="text-[9px] font-medium uppercase tracking-wide text-muted-foreground">
                        {period}
                      </span>
                    )}
                  </div>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content
                    side="bottom"
                    sideOffset={4}
                    className="z-50 max-w-xs rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
                  >
                    <div className="font-medium text-foreground">{c.display_name}</div>
                    {(c.description || c.aggregation) && (
                      <div className="mt-1 leading-snug text-muted-foreground">
                        {c.description || c.aggregation}
                      </div>
                    )}
                    <Tooltip.Arrow className="fill-background" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
            );
          })}

          {/* Data rows */}
          {rows.map((r) =>
            renderRow({ row: r, cols: numericCols, maxByCol }),
          )}
        </div>
      </div>
    </section>
  );
}

function renderRow({
  row,
  cols,
  maxByCol,
}: {
  row: AERow;
  cols: ColumnMeta[];
  maxByCol: Record<string, number>;
}) {
  return (
    <>
      <div
        key={`r-${row.ae_id}`}
        className="sticky left-0 z-10 truncate bg-background px-2 py-2 text-xs"
        title={row.ae_name}
      >
        {row.ae_name}
      </div>
      {cols.map((c) => {
        const v = row.values[c.col_id];
        const max = maxByCol[c.col_id] || 1;
        const hasValue = v != null && Number.isFinite(v);
        let norm: number | null = null;
        if (hasValue) {
          const raw = Math.min(1, Math.max(0, Math.abs(v as number) / max));
          norm = LOWER_IS_BETTER.has(c.col_id) ? 1 - raw : raw;
        }
        return (
          <Tooltip.Root key={`${row.ae_id}-${c.col_id}`}>
            <Tooltip.Trigger asChild>
              <div
                className="h-8 cursor-help transition-[box-shadow] hover:shadow-[inset_0_0_0_2px_rgba(0,0,0,0.65)]"
                style={
                  hasValue
                    ? { backgroundColor: rdylgnFor(norm) }
                    : {
                        backgroundColor: "rgb(248,250,252)",
                        backgroundImage:
                          "repeating-linear-gradient(45deg, rgba(0,0,0,0) 0 5px, rgba(0,0,0,0.04) 5px 6px)",
                      }
                }
                aria-label={`${row.ae_name} — ${c.display_name}: ${fmt(v, c.format)}`}
              />
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                side="top"
                sideOffset={4}
                className="z-50 max-w-xs rounded-md border border-border bg-background px-2.5 py-1.5 text-xs shadow-md"
              >
                <div className="font-medium text-foreground">
                  {row.ae_name} — {c.display_name}
                </div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  {hasValue ? fmt(v, c.format) : "no data"}
                </div>
                {c.description && (
                  <div className="mt-1 leading-snug text-muted-foreground">
                    {c.description}
                  </div>
                )}
                <Tooltip.Arrow className="fill-background" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        );
      })}
    </>
  );
}

/** Render a tiny gradient bar legend on the right of the section header. */
function Legend() {
  const stops = [0, 0.25, 0.5, 0.75, 1];
  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
      <span>Worse</span>
      <div className="flex h-3 w-32 overflow-hidden rounded border border-border">
        {stops.map((s) => (
          <div
            key={s}
            className="h-full flex-1"
            style={{ backgroundColor: rdylgnFor(s) }}
          />
        ))}
      </div>
      <span>Better</span>
      <span className="ml-2 inline-flex items-center gap-1">
        <span
          className="inline-block h-3 w-3 rounded-sm border border-border"
          style={{
            backgroundColor: "rgb(248,250,252)",
            backgroundImage:
              "repeating-linear-gradient(45deg, rgba(0,0,0,0) 0 4px, rgba(0,0,0,0.04) 4px 5px)",
          }}
        />
        <span>No data</span>
      </span>
    </div>
  );
}

/**
 * Build a compact column header: a primary line (display name with common
 * words abbreviated) plus an optional period marker on a second line.
 *
 * "Quota (YTD)"               → primary "Quota",           period "YTD"
 * "Bookings (MTD)"            → primary "Bookings",        period "MTD"
 * "Quota Attainment % (YTD)"  → primary "Attain %",        period "YTD"
 * "Open Pipeline (This Mo.)"  → primary "Open Pipe",       period "This Mo"
 * "Self-Gen Pipeline (Per.)"  → primary "SG Pipe",         period ""
 * "Unique Email Recipients"   → primary "Email Recip",     period ""
 */
function makeShortLabel(c: ColumnMeta): { primary: string; period: string } {
  const display = c.display_name || c.col_id;
  const periodMatch = display.match(/\(([^)]+)\)/);
  const period = periodMatch ? shortPeriod(periodMatch[1]) : "";

  let base = display.replace(/\([^)]*\)/g, "").trim();
  const replacements: [RegExp, string][] = [
    [/\bSelf-Gen\b/gi, "SG"],
    [/\bChannel Partner(s)?\b/gi, "CP"],
    [/\bMarketing\b/g, "Mkt"],
    [/\bTotal\s+/gi, ""],
    [/\bUnique\s+/gi, ""],
    [/\bPipeline\b/gi, "Pipe"],
    [/\bBookings?\b/gi, "Bookings"],
    [/\bOpportunities\b/gi, "Opps"],
    [/\bAttainment\b/gi, "Attain"],
    [/\bRecipients?\b/gi, "Recip"],
    [/\bMeetings?\s+Held\b/gi, "Mtgs Held"],
    [/\bMeetings?\s+Scheduled\b/gi, "Mtgs Sched"],
    [/\bAccounts?\s+w\//gi, "Accts w/"],
    [/\bVoicemails?\b/gi, "Vmail"],
  ];
  for (const [re, sub] of replacements) base = base.replace(re, sub);
  base = base.replace(/\s+/g, " ").trim();

  return { primary: base, period };
}

function shortPeriod(p: string): string {
  const l = p.toLowerCase().trim();
  if (l === "ytd" || l === "mtd" || l === "qtd") return l.toUpperCase();
  if (l === "period") return "";
  if (l.includes("this month")) return "This Mo";
  if (l.includes("next month")) return "Next Mo";
  if (l.includes("last month")) return "Last Mo";
  return p.length > 8 ? p.slice(0, 8) : p;
}
