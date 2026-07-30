import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";

interface BackendStatus {
  status: "checking" | "ok" | "error";
  version?: string;
}

// Metric card component — placeholder until Epic 2
function MetricCard({
  label, value, change, icon
}: {
  label: string;
  value: string;
  change?: string;
  positive?: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-50 text-sky-500 dark:bg-sky-900/30">
          {icon}
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
        {change && (
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{change}</p>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [backend, setBackend] = useState<BackendStatus>({ status: "checking" });

  useEffect(() => {
    fetch("/api/v1/health")
      .then((r) => r.json())
      .then(() =>
        fetch("/api/v1/version")
          .then((r) => r.json())
          .then((v) => setBackend({ status: "ok", version: v.version }))
      )
      .catch(() => setBackend({ status: "error" }));
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome banner */}
      <div className="rounded-xl bg-gradient-to-r from-sky-500 to-sky-600 p-6 text-white shadow-sm">
        <h2 className="text-xl font-bold">Welcome to Personal CFO AI 👋</h2>
        <p className="mt-1 text-sky-100">
          Epic 1 · Foundation — platform is ready. Portfolio features coming in Epic 2.
        </p>
        <div className="mt-3 flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1 text-xs font-medium">
            {backend.status === "checking" && <Spinner size="sm" className="text-white" />}
            {backend.status === "ok" && <span className="h-2 w-2 rounded-full bg-emerald-300" />}
            {backend.status === "error" && <span className="h-2 w-2 rounded-full bg-red-300" />}
            Backend {backend.status === "ok" ? `v${backend.version}` : backend.status}
          </span>
        </div>
      </div>

      {/* Metric cards — placeholder data */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total Portfolio"
          value="—"
          change="Connect your portfolio in Epic 2"
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <MetricCard
          label="Today's P&L"
          value="—"
          change="Market data in Epic 3"
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
        />
        <MetricCard
          label="Active Goals"
          value="—"
          change="Set your goals in Epic 7"
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <MetricCard
          label="AI Insights"
          value="—"
          change="AI agents in Epic 4"
          icon={<svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>}
        />
      </div>

      {/* Two-column section */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Recent Transactions" subtitle="Your latest portfolio activity" />
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-slate-400">Transactions will appear here in Epic 2</p>
          </div>
        </Card>

        <Card>
          <CardHeader title="Watchlist" subtitle="Stocks you're tracking" />
          <div className="flex h-32 items-center justify-center">
            <p className="text-sm text-slate-400">Watchlist will appear here in Epic 2</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
