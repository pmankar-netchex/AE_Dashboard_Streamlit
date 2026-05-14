import { cn } from "@/lib/cn";

interface Props {
  /** When true, render just the mark (no wordmark). For collapsed sidebar. */
  iconOnly?: boolean;
  size?: number;
  className?: string;
}

/**
 * App logo — square mark with "AE" + an ascending bar-chart motif, plus
 * an optional wordmark beside it. Matches the favicon (public/favicon.svg).
 */
export function Logo({ iconOnly = false, size = 28, className }: Props) {
  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <svg
        viewBox="0 0 32 32"
        width={size}
        height={size}
        aria-hidden="true"
        className="shrink-0"
      >
        <defs>
          <linearGradient id="logo-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1e3a8a" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="32" height="32" rx="7" fill="url(#logo-bg)" />
        <text
          x="16"
          y="17"
          textAnchor="middle"
          fontFamily="-apple-system, Segoe UI, Roboto, sans-serif"
          fontWeight={700}
          fontSize="13"
          fill="#fff"
          letterSpacing="-0.5"
        >
          AE
        </text>
        <g fill="#22c55e">
          <rect x="6" y="24" width="3" height="3" rx="0.5" />
          <rect x="11" y="22" width="3" height="5" rx="0.5" />
          <rect x="16" y="20" width="3" height="7" rx="0.5" />
          <rect x="21" y="22" width="3" height="5" rx="0.5" />
        </g>
      </svg>
      {!iconOnly && (
        <span className="flex min-w-0 flex-col leading-tight">
          <span className="truncate whitespace-nowrap text-sm font-semibold text-foreground">
            AE Dashboard
          </span>
          <span className="truncate whitespace-nowrap text-[10px] text-muted-foreground">
            Performance Analytics
          </span>
        </span>
      )}
    </div>
  );
}
