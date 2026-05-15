import { Outlet } from "@tanstack/react-router";
import { Toaster } from "sonner";
import { useMe } from "@/hooks/useMe";
import { NoAccessPage } from "@/pages/NoAccessPage";
import { SideNav } from "./SideNav";

export function AppShell() {
  const me = useMe();

  // 403 → user has authenticated with Entra (Easy Auth let them through) but
  // isn't in the app's users table. Show the access-request screen instead
  // of a broken dashboard.
  if (me.error && me.error.status === 403) {
    return <NoAccessPage />;
  }

  return (
    <div className="flex h-full">
      <SideNav />
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
      <Toaster richColors closeButton position="top-right" />
    </div>
  );
}
