import { AEMultiSelect } from "./AEMultiSelect";
import { ManagerSelect } from "./ManagerSelect";
import { RefreshButton } from "./RefreshButton";
import { TimePeriodPicker } from "./TimePeriodPicker";

/**
 * Single-line page header for dashboard pages: title/subtitle on the left,
 * unified filter chips + refresh on the right.
 */
export function FilterBar({
  title,
  subtitle,
}: {
  title?: string;
  subtitle?: string;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
      <div className="flex flex-wrap items-center gap-3 px-6 py-3">
        {title && (
          <div className="mr-auto min-w-0">
            <h1 className="truncate text-base font-semibold text-foreground">
              {title}
            </h1>
            {subtitle && (
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {subtitle}
              </p>
            )}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <ManagerSelect />
          <AEMultiSelect />
          <TimePeriodPicker />
          <span className="mx-1 h-6 w-px bg-border" aria-hidden="true" />
          <RefreshButton iconOnly />
        </div>
      </div>
    </header>
  );
}
