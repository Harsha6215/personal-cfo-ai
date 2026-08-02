import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";

interface WatchlistInsight {
  ticker: string;
  name: string;
  current_price: number;
  change_pct: number;
  signal: string;
  signal_reason: string;
  risk_level: string;
  composite_score: number | null;
  alerts: string[];
}

interface WatchlistReport {
  items: WatchlistInsight[];
  actionable_count: number;
  total_items: number;
  summary: string;
}

export default function Watchlist() {
  const [report, setReport] = useState<WatchlistReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [addSymbol, setAddSymbol] = useState("");
  const [adding, setAdding] = useState(false);

  const fetchWatchlist = () => {
    const token = getStoredToken();
    fetch("/api/v1/decisions/watchlist", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setReport(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchWatchlist(); }, []);

  const handleAdd = async () => {
    if (!addSymbol.trim()) return;
    setAdding(true);
    const token = getStoredToken();
    try {
      await fetch("/api/v1/assets/watchlist", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: addSymbol.trim().toUpperCase() }),
      });
      setAddSymbol("");
      fetchWatchlist();
    } catch { /* ignore */ }
    finally { setAdding(false); }
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  const signalColor = (signal: string) => {
    switch (signal) {
      case "ENTRY": return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300";
      case "EXIT": return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300";
      case "WATCH": return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300";
      default: return "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Watchlist</h1>
          <p className="text-sm text-slate-500">{report?.summary || "Track stocks with AI intelligence"}</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Add ticker..."
            value={addSymbol}
            onChange={e => setAddSymbol(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleAdd()}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
          <button onClick={handleAdd} disabled={adding} className="btn-primary text-sm">
            {adding ? "..." : "+ Add"}
          </button>
        </div>
      </div>

      {report?.actionable_count ? (
        <div className="rounded-lg bg-sky-50 px-4 py-3 text-sm text-sky-800 dark:bg-sky-900/20 dark:text-sky-300">
          🎯 {report.actionable_count} stock{report.actionable_count > 1 ? "s" : ""} with actionable signals
        </div>
      ) : null}

      {/* Watchlist table */}
      {report?.items && report.items.length > 0 ? (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="py-3 pr-4 text-left font-medium text-slate-500">Stock</th>
                  <th className="py-3 px-2 text-right font-medium text-slate-500">Price</th>
                  <th className="py-3 px-2 text-right font-medium text-slate-500">Change</th>
                  <th className="py-3 px-2 text-center font-medium text-slate-500">Signal</th>
                  <th className="py-3 pl-4 text-left font-medium text-slate-500">Reason</th>
                </tr>
              </thead>
              <tbody>
                {report.items.map(item => (
                  <tr key={item.ticker} className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="py-3 pr-4">
                      <Link to={`/stock/${item.ticker}`} className="font-medium text-sky-600 hover:text-sky-500 dark:text-sky-400">
                        {item.ticker}
                      </Link>
                      <p className="text-xs text-slate-400 truncate max-w-[150px]">{item.name}</p>
                    </td>
                    <td className="py-3 px-2 text-right font-mono">₹{item.current_price.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                    <td className={`py-3 px-2 text-right font-mono font-semibold ${item.change_pct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {item.change_pct >= 0 ? "+" : ""}{item.change_pct.toFixed(2)}%
                    </td>
                    <td className="py-3 px-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${signalColor(item.signal)}`}>
                        {item.signal}
                      </span>
                    </td>
                    <td className="py-3 pl-4 text-xs text-slate-600 dark:text-slate-400 max-w-[200px] truncate">
                      {item.signal_reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <p className="text-slate-400">No watchlist items yet. Add a ticker above to start tracking.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
