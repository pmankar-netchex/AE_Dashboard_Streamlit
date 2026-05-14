import { Outlet } from "@tanstack/react-router";
import { SideNav } from "./SideNav";
import { TopBar } from "./TopBar";

export function AppShell() {
  return (
    <div className="flex h-full">
      <SideNav />
      <div className="flex flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
