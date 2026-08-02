import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";

interface RankedStock {
  rank: number;
  ticker: string;
  name: string;
  action: string;
  composite_score: number;
  confidence: number;
  momentum_score: number;
  value_score: number;
  risk_score: number;
  suggested_action: string;
}

interface Opportunity {
  ticker: string;
  name: string;
  opportunity_type: string;
  score: number;
  reason: string;
  entry_price: number | null;
  upside_pct: number | null;
  risk_level: string;
}

export default function Research() {
  const [buyList, setBuyList] = useState<RankedStock[]>([]);
  const [sellList, setSellList] = useState<RankedStock[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"rankings" | "opportunities">("rankings");

  useEffect(() => {
    const token = getStoredToken();
    const headers = { Authorization: `Bearer ${token}` };

    Promise.allSettled([
      fetch("/api/v1/decisions/rankings", { headers }).then(r => r.ok ? r.json() : null),
      fetch("/api/v1/decisions/opportunities", { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([rankRes, oppRes]) => {
      if (rankRes.status === "fulfilled" && rankRes.value) {
        setBuyList(rankRes.value.buy_list || []);
        setSellList(rankRes.value.sell_list || []);
      }
      if (oppRes.status === "fulfilled" && oppRes.value) {
        setOpportunities(oppRes.value.opportunities || []);
      }
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Research</h1>
        <p className="text-sm text-slate-500">Buy/Sell rankings and opportunity scanner</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setTab("rankings")}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === "rankings" ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
          }`}
        >📊 Buy/Sell Rankings</button>
        <button
          onClick={() => setTab("opportunities")}
          className={`rounded-lg px-4 py-2 text-sm font-medium ${
            tab === "opportunities" ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
          }`}
        >🔍 Opportunities</button>
      </div>

      {tab === "rankings" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Buy List */}
          <Card>
            <CardHeader title="🟢 Buy List" subtitle={`${buyList.length} stocks`} />
            {buyList.length > 0 ? (
              <div className="space-y-2">
                {buyList.map(s => (
                  <div key={s.ticker} className="flex items-center justify-between rounded-lg border border-emerald-100 bg-emerald-50/50 px-3 py-2 dark:border-emerald-800 dark:bg-emerald-900/10">
                    <div>
                      <Link to={`/stock/${s.ticker}`} className="font-medium text-sky-600 hover:text-sky-500 dark:text-sky-400">{s.ticker}</Link>
                      <p className="text-xs text-slate-500 truncate max-w-[120px]">{s.name}</p>
                    </div>
                    <div className="text-right">
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
                        {s.composite_score.toFixed(1)}/10
                      </span>
                      <p className="mt-0.5 text-xs text-slate-400">{s.confidence.toFixed(0)}% conf</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-slate-400 py-4 text-center">No buy signals</p>}
          </Card>

          {/* Sell List */}
          <Card>
            <CardHeader title="🔴 Sell List" subtitle={`${sellList.length} stocks`} />
            {sellList.length > 0 ? (
              <div className="space-y-2">
                {sellList.map(s => (
                  <div key={s.ticker} className="flex items-center justify-between rounded-lg border border-red-100 bg-red-50/50 px-3 py-2 dark:border-red-800 dark:bg-red-900/10">
                    <div>
                      <Link to={`/stock/${s.ticker}`} className="font-medium text-sky-600 hover:text-sky-500 dark:text-sky-400">{s.ticker}</Link>
                      <p className="text-xs text-slate-500 truncate max-w-[120px]">{s.name}</p>
                    </div>
                    <div className="text-right">
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700 dark:bg-red-900 dark:text-red-300">
                        {s.composite_score.toFixed(1)}/10
                      </span>
                      <p className="mt-0.5 text-xs text-slate-400">{s.suggested_action}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-slate-400 py-4 text-center">No sell signals</p>}
          </Card>
        </div>
      )}

      {tab === "opportunities" && (
        <Card>
          <CardHeader title="Opportunity Scanner" subtitle={`${opportunities.length} opportunities found`} />
          {opportunities.length > 0 ? (
            <div className="space-y-3">
              {opportunities.map((opp, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3 dark:border-slate-700">
                  <div>
                    <Link to={`/stock/${opp.ticker}`} className="font-medium text-sky-600 hover:text-sky-500 dark:text-sky-400">{opp.ticker}</Link>
                    <span className="ml-2 text-xs text-slate-400">{opp.name}</span>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{opp.reason}</p>
                    <div className="mt-1 flex gap-2">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 dark:bg-slate-700">{opp.opportunity_type}</span>
                      <span className={`rounded px-1.5 py-0.5 text-xs ${
                        opp.risk_level === "LOW" ? "bg-emerald-100 text-emerald-700" :
                        opp.risk_level === "HIGH" ? "bg-red-100 text-red-700" :
                        "bg-amber-100 text-amber-700"
                      }`}>{opp.risk_level} risk</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-lg font-bold text-sky-600 dark:text-sky-400">{opp.score.toFixed(0)}</span>
                    <p className="text-xs text-slate-400">score</p>
                    {opp.upside_pct && <p className="text-xs text-emerald-600">↑{opp.upside_pct.toFixed(0)}%</p>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-slate-400">No opportunities found. Add stocks to your watchlist to scan.</p>
          )}
        </Card>
      )}
    </div>
  );
}
