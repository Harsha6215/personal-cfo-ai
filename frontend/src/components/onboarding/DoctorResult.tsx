import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { getStoredToken } from "@/services/auth";

interface Props {
  onComplete: () => void;
  loading: boolean;
}

interface DoctorData {
  total_holdings: number;
  total_invested: number;
  allocation: Record<string, number>;
  risk_score: number;
  concerns: string[];
  recommendations: string[];
}

export function DoctorResult({ onComplete, loading }: Props) {
  const [doctor, setDoctor] = useState<DoctorData | null>(null);
  const [analyzing, setAnalyzing] = useState(true);

  useEffect(() => {
    analyzePortfolio();
  }, []);

  const analyzePortfolio = async () => {
    const token = getStoredToken();
    if (!token) {
      setAnalyzing(false);
      return;
    }

    try {
      // Get portfolio holdings
      const portfolioRes = await fetch("/api/v1/portfolios", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const portfolios = await portfolioRes.json();

      if (portfolios.length === 0) {
        setDoctor({
          total_holdings: 0,
          total_invested: 0,
          allocation: {},
          risk_score: 50,
          concerns: ["No portfolio data found. Upload your holdings to get personalized analysis."],
          recommendations: ["Import your broker's holdings CSV for a full portfolio analysis."],
        });
        setAnalyzing(false);
        return;
      }

      // Get holdings for first portfolio
      const holdingsRes = await fetch(`/api/v1/portfolios/${portfolios[0].id}/holdings`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!holdingsRes.ok) {
        throw new Error("Failed to load holdings");
      }

      const holdings = await holdingsRes.json();

      // Calculate basic allocation
      const allocation: Record<string, number> = {};
      for (const h of holdings.holdings || []) {
        const type = h.asset_type || "OTHER";
        allocation[type] = (allocation[type] || 0) + h.invested_value;
      }

      // Normalize to percentages
      const total = Object.values(allocation).reduce((a, b) => a + b, 0);
      const pctAllocation: Record<string, number> = {};
      for (const [k, v] of Object.entries(allocation)) {
        pctAllocation[k] = total > 0 ? Math.round((v / total) * 100) : 0;
      }

      // Simple risk score based on concentration
      const maxPct = Math.max(...Object.values(pctAllocation), 0);
      const riskScore = Math.min(100, Math.max(20, maxPct + (holdings.total_holdings < 5 ? 20 : 0)));

      // Generate concerns and recommendations
      const concerns: string[] = [];
      const recommendations: string[] = [];

      if (holdings.total_holdings < 5) {
        concerns.push("Low diversification — fewer than 5 holdings");
        recommendations.push("Consider adding 10-15 stocks across different sectors");
      }
      if (maxPct > 40) {
        concerns.push(`High concentration — one sector is ${maxPct}% of portfolio`);
        recommendations.push("Rebalance to limit any single sector to 30% max");
      }
      if (Object.keys(pctAllocation).length < 3) {
        concerns.push("Limited asset class diversity");
        recommendations.push("Add debt instruments or gold for better risk-adjusted returns");
      }
      if (concerns.length === 0) {
        recommendations.push("Portfolio looks well-diversified! Keep monitoring quarterly.");
      }

      setDoctor({
        total_holdings: holdings.total_holdings,
        total_invested: holdings.total_invested,
        allocation: pctAllocation,
        risk_score: riskScore,
        concerns,
        recommendations,
      });
    } catch {
      setDoctor({
        total_holdings: 0,
        total_invested: 0,
        allocation: {},
        risk_score: 50,
        concerns: ["Could not analyze portfolio. You can always access the Portfolio Doctor from the dashboard."],
        recommendations: [],
      });
    } finally {
      setAnalyzing(false);
    }
  };

  if (analyzing) {
    return (
      <div className="text-center py-8">
        <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-slate-600 border-t-sky-500" />
        <p className="text-sm text-slate-400">Analyzing your portfolio…</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-2">Portfolio Doctor</h2>
      <p className="text-sm text-slate-400 mb-5">Here's your portfolio health assessment</p>

      {doctor && (
        <>
          {/* Risk score gauge */}
          <div className="mb-5 flex items-center gap-4 rounded-xl border border-slate-700 bg-slate-700/30 p-4">
            <div className="relative h-16 w-16">
              <svg className="h-16 w-16 -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-slate-700"
                  strokeWidth="3"
                  fill="none"
                  stroke="currentColor"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className={doctor.risk_score > 60 ? "text-amber-500" : "text-emerald-500"}
                  strokeWidth="3"
                  fill="none"
                  stroke="currentColor"
                  strokeDasharray={`${doctor.risk_score}, 100`}
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
                {doctor.risk_score}
              </span>
            </div>
            <div>
              <div className="text-sm font-medium text-white">Risk Score</div>
              <div className="text-xs text-slate-400">
                {doctor.risk_score > 70 ? "High risk" : doctor.risk_score > 40 ? "Moderate" : "Low risk"}
              </div>
              {doctor.total_holdings > 0 && (
                <div className="mt-1 text-xs text-slate-500">
                  {doctor.total_holdings} holdings · ₹{(doctor.total_invested / 100000).toFixed(1)}L invested
                </div>
              )}
            </div>
          </div>

          {/* Allocation pie (text-based) */}
          {Object.keys(doctor.allocation).length > 0 && (
            <div className="mb-5">
              <h3 className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wider">Allocation</h3>
              <div className="space-y-1.5">
                {Object.entries(doctor.allocation).map(([type, pct]) => (
                  <div key={type} className="flex items-center gap-2">
                    <div className="h-2 flex-1 rounded-full bg-slate-700 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-sky-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 w-20 text-right">{type}</span>
                    <span className="text-xs text-white w-8 text-right">{pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Concerns */}
          {doctor.concerns.length > 0 && (
            <div className="mb-4">
              <h3 className="text-xs font-medium text-amber-400 mb-2">⚠️ Concerns</h3>
              <ul className="space-y-1">
                {doctor.concerns.map((c, i) => (
                  <li key={i} className="text-xs text-slate-400 pl-3 border-l-2 border-amber-500/40">
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {doctor.recommendations.length > 0 && (
            <div className="mb-6">
              <h3 className="text-xs font-medium text-emerald-400 mb-2">💡 Quick Wins</h3>
              <ul className="space-y-1">
                {doctor.recommendations.map((r, i) => (
                  <li key={i} className="text-xs text-slate-400 pl-3 border-l-2 border-emerald-500/40">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      <Button variant="primary" className="w-full" onClick={onComplete} loading={loading}>
        Complete Setup & Go to Dashboard
      </Button>
    </div>
  );
}
