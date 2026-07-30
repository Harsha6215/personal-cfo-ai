import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/portfolio": "Portfolio",
  "/watchlist": "Watchlist",
  "/research": "Research",
  "/goals": "Goals",
  "/advisor": "AI Advisor",
  "/settings": "Settings",
};

export function AppShell() {
  const { pathname } = useLocation();
  const title = pageTitles[pathname] ?? "Personal CFO AI";

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-900">
      <Sidebar />
      {/* Main area — offset by sidebar width */}
      <div className="flex flex-1 flex-col overflow-hidden pl-64">
        <TopBar title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
