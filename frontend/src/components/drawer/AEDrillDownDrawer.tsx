import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useFilters } from "@/hooks/useFilters";
import { useAeDetail, useColumnMeta } from "@/hooks/useDashboard";
import { fmt } from "@/lib/formatters";

export function AEDrillDownDrawer() {
  const { filters, set } = useFilters();
  const cols = useColumnMeta();
  const detail = useAeDetail(filters.aeDrillId, filters);
  const open = !!filters.aeDrillId;

  const close = (): void => {
    set({ aeDrillId: null });
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => (o ? null : close())}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30 data-[state=open]:animate-in data-[state=closed]:animate-out" />
        <Dialog.Content
          className="fixed right-0 top-0 z-50 h-full w-full overflow-y-auto bg-background shadow-2xl sm:w-[640px] lg:w-[840px]"
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
            <div>
              <Dialog.Title className="text-base font-semibold">
                {detail.data?.ae_name ?? "Loading…"}
              </Dialog.Title>
              <Dialog.Description asChild>
                <div className="text-xs text-muted-foreground">
                  {detail.data ? (
                    <>
                      <div>
                        Manager: {detail.data.ae_manager || "—"} • {detail.data.ae_email}
                      </div>
                      <div>SDR: {detail.data.sdr_name || "—"}</div>
                    </>
                  ) : (
                    "Fetching AE detail"
                  )}
                </div>
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="space-y-6 px-4 py-4">
            {detail.isError && (
              <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
                {(detail.error as Error).message}
              </div>
            )}

            {detail.data && (
              <>
                <section>
                  <h3 className="mb-2 text-sm font-medium text-muted-foreground">
                    Source Breakdown
                  </h3>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
                      <span className="font-medium">Total Pipeline (Period)</span>
                      <span className="tabular-nums">
                        {fmt(detail.data.all_source_summary.total_pipeline, "currency")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
                      <span className="font-medium">Total Bookings (Period)</span>
                      <span className="tabular-nums">
                        {fmt(detail.data.all_source_summary.total_bookings, "currency")}
                      </span>
                    </div>
                    {detail.data.all_source_summary.sources.map((s) => (
                      <div
                        key={s.label}
                        className="grid grid-cols-3 items-center rounded-md border border-border px-3 py-2 text-sm"
                      >
                        <span className="font-medium">{s.label}</span>
                        <span className="text-right tabular-nums">
                          <span className="text-xs text-muted-foreground">Pipe </span>
                          {fmt(s.pipeline, "currency")}
                        </span>
                        <span className="text-right tabular-nums">
                          <span className="text-xs text-muted-foreground">Book </span>
                          {fmt(s.bookings, "currency")}
                        </span>
                      </div>
                    ))}
                  </div>
                </section>

                {cols.data && (
                  <section>
                    <h3 className="mb-2 text-sm font-medium text-muted-foreground">
                      Sections
                    </h3>
                    <div className="space-y-3">
                      {cols.data.sections.map((sec) => {
                        const secCols = cols.data!.columns.filter(
                          (c) => c.section === sec.key,
                        );
                        return (
                          <details key={sec.key} className="rounded-md border border-border">
                            <summary className="cursor-pointer px-3 py-2 text-sm font-medium hover:bg-accent">
                              {sec.display_name}
                            </summary>
                            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 px-3 py-3 text-xs">
                              {secCols.map((c) => (
                                <div
                                  key={c.col_id}
                                  className="flex items-center justify-between border-b border-border/40 py-1"
                                >
                                  <dt className="truncate text-muted-foreground" title={c.description}>
                                    {c.display_name}
                                  </dt>
                                  <dd className="tabular-nums">
                                    {c.blocked
                                      ? "Pending"
                                      : fmt(detail.data!.values[c.col_id], c.format)}
                                  </dd>
                                </div>
                              ))}
                            </dl>
                          </details>
                        );
                      })}
                    </div>
                  </section>
                )}
              </>
            )}

            {detail.isLoading && (
              <div className="rounded-lg border border-border p-6 text-center text-sm text-muted-foreground">
                Loading AE detail…
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
