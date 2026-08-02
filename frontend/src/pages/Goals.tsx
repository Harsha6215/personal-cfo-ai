import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";

interface AllocationSlot {
  ticker: string;
  name: string;
  target_pct: number;
  actual_pct: number;
  drift_pct: number;
  action: string;
  amount_to_adjust: number;
}

interface AllocationPlan {
  strategy: string;
  total_value: number;
  slots: AllocationSlot[];
  max_drift: number;
  needs_rebalance: boolean;
  summary: string;
  sector_allocation: Record<string, number>;
}

interface RebalanceOrder {
  ticker: string;
  name: string;
  action: string;
  quantity: number;
  estimated_price: number;
  estimated_amount: number;
  reason: string;
  priority: number;
}

interface RebalancePlan {
  orders: RebalanceOrder[];
  total_buy_amount: number;
  total_sell_amount: number;
  net_cash_needed: number;
  estimated_charges: number;
  tax_note: string;
  summary: string;
}

export default function Goals() {
  const [allocation, setAllocation] = useState<AllocationPlan | null>(null);
  const [rebalancePlan, setRebalancePlan] = useState<RebalancePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [rebalancing, setRebalancing] = useState(false);

  useEffect(() => {
    const token = getStoredToken();
    fetch("/api/v1/decisions/allocation", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setAllocation(data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const generateRebalance = async () => {
    setRebalancing(true);
    const token = getStoredToken();
    try {
      const res = await fetch("/api/v1/decisions/rebalance", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ available_cash: 0, strategy: "equal_weight" }),
      });
      if (res.ok) setRebalancePlan(await res.json());
    } catch { /* ignore */ }
    finally { setRebalancing(false); }
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Allocation & Rebalance</h1>
          <p className="text-sm text-slate-500">{allocation?.summary || "Target vs actual allocation"}</p>
        </div>
        {allocation?.needs_rebalance && (
          <button onClick={generateRebalance} disabled={rebalancing} className="btn-primary text-sm">
            {rebalancing ? "Generating..." : "⚖️ Generate Rebalance Plan"}
          </button>
        )}
      </div>

      {/* Allocation Status */}
      {allocation && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <div className="text-center py-2">
              <p className="text-xs text-slate-500">Strategy</p>
              <p className="text-lg font-semibold capitalize">{allocation.strategy.replace("_", " ")}</p>
            </div>
          </Card>
          <Card>
            <div className="text-center py-2">
              <p className="text-xs text-slate-500">Max Drift</p>
              <p className={`text-lg font-semibold ${allocation.max_drift > 5 ? "text-amber-600" : "text-emerald-600"}`}>
                {allocation.max_drift.toFixed(1)}%
              </p>
            </div>
          </Card>
          <Card>
            <div className="text-center py-2">
              <p className="text-xs text-slate-500">Status</p>
              <p className={`text-lg font-semibold ${allocation.needs_rebalance ? "text-amber-600" : "text-emerald-600"}`}>
                {allocation.needs_rebalance ? "Rebalance Needed" : "On Target"}
              </p>
            </div>
          </Card>
        </div>
      )}

      {/* Allocation Table */}
      {allocation?.slots && allocation.slots.length > 0 && (
        <Card>
          <CardHeader title="Allocation Drift" subtitle="Target vs actual position sizes" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="py-2 text-left font-medium text-slate-500">Ticker</th>
                  <th className="py-2 text-right font-medium text-slate-500">Target</th>
                  <th className="py-2 text-right font-medium text-slate-500">Actual</th>
                  <th className="py-2 text-right font-medium text-slate-500">Drift</th>
                  <th className="py-2 text-center font-medium text-slate-500">Action</th>
                </tr>
              </thead>
              <tbody>
                {allocation.slots.map(s => (
                  <tr key={s.ticker} className="border-b border-slate-100 dark:border-slate-700/50">
                    <td className="py-2 font-medium text-slate-900 dark:text-slate-100">{s.ticker}</td>
                    <td className="py-2 text-right font-mono text-slate-600 dark:text-slate-400">{s.target_pct.toFixed(1)}%</td>
                    <td className="py-2 text-right font-mono text-slate-600 dark:text-slate-400">{s.actual_pct.toFixed(1)}%</td>
                    <td className={`py-2 text-right font-mono font-semibold ${
                      s.drift_pct > 0 ? "text-amber-600" : s.drift_pct < 0 ? "text-sky-600" : "text-slate-400"
                    }`}>{s.drift_pct > 0 ? "+" : ""}{s.drift_pct.toFixed(1)}%</td>
                    <td className="py-2 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        s.action === "TRIM" ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" :
                        s.action === "BUY_MORE" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" :
                        "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                      }`}>{s.action.replace("_", " ")}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Sector Allocation */}
      {allocation?.sector_allocation && Object.keys(allocation.sector_allocation).length > 0 && (
        <Card>
          <CardHeader title="Sector Allocation" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Object.entries(allocation.sector_allocation).map(([sector, pct]) => (
              <div key={sector} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-700/50">
                <p className="text-xs text-slate-500">{sector}</p>
                <p className="text-sm font-semibold">{pct.toFixed(1)}%</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Rebalance Plan */}
      {rebalancePlan && (
        <Card>
          <CardHeader title="⚖️ Rebalance Plan" subtitle={rebalancePlan.summary} />
          <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
            <div className="rounded-lg bg-emerald-50 p-3 dark:bg-emerald-900/20">
              <p className="text-xs text-slate-500">Total Buy</p>
              <p className="font-semibold text-emerald-700 dark:text-emerald-300">₹{rebalancePlan.total_buy_amount.toLocaleString("en-IN")}</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
              <p className="text-xs text-slate-500">Total Sell</p>
              <p className="font-semibold text-red-700 dark:text-red-300">₹{rebalancePlan.total_sell_amount.toLocaleString("en-IN")}</p>
            </div>
            <div className="rounded-lg bg-sky-50 p-3 dark:bg-sky-900/20">
              <p className="text-xs text-slate-500">Net Cash Needed</p>
              <p className="font-semibold">₹{rebalancePlan.net_cash_needed.toLocaleString("en-IN")}</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
              <p className="text-xs text-slate-500">Est. Charges</p>
              <p className="font-semibold">₹{rebalancePlan.estimated_charges.toFixed(0)}</p>
            </div>
          </div>

          {rebalancePlan.orders.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="py-2 text-left text-slate-500">#</th>
                    <th className="py-2 text-left text-slate-500">Ticker</th>
                    <th className="py-2 text-center text-slate-500">Action</th>
                    <th className="py-2 text-right text-slate-500">Qty</th>
                    <th className="py-2 text-right text-slate-500">Amount</th>
                    <th className="py-2 text-left text-slate-500">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {rebalancePlan.orders.map(o => (
                    <tr key={o.ticker + o.action} className="border-b border-slate-100 dark:border-slate-700/50">
                      <td className="py-2 text-slate-400">{o.priority}</td>
                      <td className="py-2 font-medium">{o.ticker}</td>
                      <td className="py-2 text-center">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                          o.action === "BUY" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                        }`}>{o.action}</span>
                      </td>
                      <td className="py-2 text-right font-mono">{o.quantity}</td>
                      <td className="py-2 text-right font-mono">₹{o.estimated_amount.toLocaleString("en-IN")}</td>
                      <td className="py-2 text-xs text-slate-500">{o.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="mt-3 text-xs text-slate-400">{rebalancePlan.tax_note}</p>
        </Card>
      )}

      {!allocation && (
        <Card>
          <div className="py-12 text-center">
            <p className="text-slate-400">No portfolio data. Import transactions to see allocation analysis.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
