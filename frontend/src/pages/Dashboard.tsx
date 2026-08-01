import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { PortfolioChart } from "@/components/ui/PortfolioChart";
import { getStoredToken } from "@/services/auth";

interface Holding {
  ticker: string;
  name: string;
  quantity: number;
  average_cost: number;
  invested_value: number;
  current_price?: number;
  current_value?: number;
  pnl?: number;
  pnl_pct?: number;
}

const formatINR = (val: number) => `₹${val.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export default function Dashboard() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [totalInvested, setTotalInvested] = useState(0);
  const [totalCurrent, setTotalCurrent] = useState<number | null>(null);
  const [totalPnl, setTotalPnl] = useState<number | null>(null);
  const [holdingsCount, setHoldingsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState("there");

  useEffect(() => {
    const user = localStorage.getItem("user");
    if (user) {
      const u = JSON.parse(user);
      setUserName(u.full_name?.split(" ")[0] || u.email?.split("@")[0] || "there");
    }

    async function fetchData() {
      const token = getStoredToken();
      if (!token) { setLoading(false); return; }

      try {
        // Get portfolios
        const portfolioRes = await fetch("/api/v1/portfolios", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!portfolioRes.ok) { setLoading(false); return; }
        const portfolios = await portfolioRes.json();
        if (portfolios.length === 0) { setLoading(false); return; }

        // Get holdings
        const holdingsRes = await fetch(`/api/v1/portfolios/${portfolios[0].id}/holdings`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!holdingsRes.ok) { setLoading(false); return; }
        const data = await holdingsRes.json();

        setTotalInvested(data.total_invested);
        setHoldingsCount(data.total_holdings);
        setHoldings(data.holdings);
        setLoading(false);

        // Fetch live prices
        let cv = 0, pl = 0;
        const updated = [...data.holdings];
        for (let i = 0; i < updated.length; i++) {
          try {
            const qRes = await fetch(`/api/v1/market/quote/${updated[i].ticker}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (qRes.ok) {
              const q = await qRes.json();
              const currentValue = q.price * updated[i].quantity;
              const pnl = currentValue - updated[i].invested_value;
              updated[i] = { ...updated[i], current_price: q.price, current_value: currentValue, pnl, pnl_pct: (pnl / updated[i].invested_value) * 100 };
              cv += currentValue;
              pl += pnl;
            }
          } catch { /* skip */ }
        }
        setHoldings(updated);
        setTotalCurrent(Math.round(cv));
        setTotalPnl(Math.round(pl));
      } catch {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  const pnlPositive = (totalPnl ?? 0) >= 0;
  const topGainers = [...holdings].filter(h => h.pnl !== undefined).sort((a, b) => (b.pnl_pct ?? 0) - (a.pnl_pct ?? 0)).slice(0, 3);
  const topLosers = [...holdings].filter(h => h.pnl !== undefined).sort((a, b) => (a.pnl_pct ?? 0) - (b.pnl_pct ?? 0)).slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="rounded-xl bg-gradient-to-r from-sky-500 to-sky-600 p-6 text-white shadow-sm">
        <h2 className="text-xl font-bold">Hi {userName} 👋</h2>
        <p className="mt-1 text-sky-100">Here's your portfolio at a glance.</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <p className="text-sm text-slate-500 dark:text-slate-400">Total Invested</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{formatINR(totalInvested)}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500 dark:text-slate-400">Current Value</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">
            {totalCurrent !== null ? formatINR(totalCurrent) : <Spinner size="sm" />}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500 dark:text-slate-400">Total P&L</p>
          {totalPnl !== null ? (
            <>
              <p className={`mt-1 text-2xl font-bold ${pnlPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                {pnlPositive ? "+" : ""}{formatINR(totalPnl)}
              </p>
              <p className={`text-xs ${pnlPositive ? "text-emerald-500" : "text-red-500"}`}>
                {pnlPositive ? "+" : ""}{totalInvested > 0 ? ((totalPnl / totalInvested) * 100).toFixed(2) : 0}%
              </p>
            </>
          ) : <Spinner size="sm" />}
        </Card>
        <Card>
          <p className="text-sm text-slate-500 dark:text-slate-400">Holdings</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">{holdingsCount}</p>
          <Link to="/portfolio" className="text-xs text-sky-500 hover:text-sky-400">View all →</Link>
        </Card>
      </div>

      {/* Portfolio chart */}
      <Card>
        <CardHeader title="Portfolio Performance" subtitle="1 year" />
        <PortfolioChart days={365} />
      </Card>

      {/* Top gainers / losers */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Top Gainers" subtitle="By return %" />
          {topGainers.length > 0 ? (
            <div className="space-y-3">
              {topGainers.map(h => (
                <Link to={`/stock/${h.ticker}`} key={h.ticker} className="flex items-center justify-between rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-700">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-slate-100">{h.ticker}</p>
                    <p className="text-xs text-slate-500">{h.name}</p>
                  </div>
                  <span className="font-mono text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                    +{h.pnl_pct?.toFixed(1)}%
                  </span>
                </Link>
              ))}
            </div>
          ) : <p className="text-sm text-slate-400">Loading…</p>}
        </Card>

        <Card>
          <CardHeader title="Top Losers" subtitle="By return %" />
          {topLosers.length > 0 ? (
            <div className="space-y-3">
              {topLosers.map(h => (
                <Link to={`/stock/${h.ticker}`} key={h.ticker} className="flex items-center justify-between rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-700">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-slate-100">{h.ticker}</p>
                    <p className="text-xs text-slate-500">{h.name}</p>
                  </div>
                  <span className="font-mono text-sm font-semibold text-red-600 dark:text-red-400">
                    {h.pnl_pct?.toFixed(1)}%
                  </span>
                </Link>
              ))}
            </div>
          ) : <p className="text-sm text-slate-400">Loading…</p>}
        </Card>
      </div>
    </div>
  );
}
