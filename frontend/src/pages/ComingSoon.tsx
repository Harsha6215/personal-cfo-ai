import { useLocation } from "react-router-dom";

const epicMap: Record<string, { epic: string; title: string }> = {
  "/portfolio": { epic: "Epic 2", title: "Portfolio Aggregation" },
  "/watchlist": { epic: "Epic 2", title: "Portfolio Aggregation" },
  "/research":  { epic: "Epic 3", title: "Market Intelligence" },
  "/advisor":   { epic: "Epic 4", title: "AI Research Agents" },
  "/goals":     { epic: "Epic 7", title: "Goal Planning" },
  "/settings":  { epic: "Epic 1", title: "Foundation" },
};

export default function ComingSoon() {
  const { pathname } = useLocation();
  const info = epicMap[pathname] ?? { epic: "Future Epic", title: "Coming Soon" };

  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-sky-500/10">
        <svg className="h-8 w-8 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
          {pathname.replace("/", "").charAt(0).toUpperCase() + pathname.slice(2)}
        </h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Arriving in <span className="font-semibold text-sky-500">{info.epic} — {info.title}</span>
        </p>
      </div>
    </div>
  );
}
