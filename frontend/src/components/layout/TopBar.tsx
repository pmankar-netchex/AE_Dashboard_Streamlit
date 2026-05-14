import { useMe } from "@/hooks/useMe";

export function TopBar() {
  const { data: me, isLoading } = useMe();
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur">
      <div className="text-sm text-muted-foreground">AE Performance</div>
      <div className="flex items-center gap-3 text-sm">
        {isLoading ? (
          <span className="text-muted-foreground">…</span>
        ) : me ? (
          <>
            <span className="text-muted-foreground">{me.email}</span>
            <span className="rounded-full border border-border px-2 py-0.5 text-xs font-medium">
              {me.role}
            </span>
          </>
        ) : (
          <span className="text-muted-foreground">signed out</span>
        )}
      </div>
    </header>
  );
}
