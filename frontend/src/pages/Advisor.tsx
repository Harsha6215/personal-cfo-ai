import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { VoiceInput } from "@/components/VoiceInput";
import { getStoredToken } from "@/services/auth";

interface CIOReport {
  report_date: string;
  greeting: string;
  market: {
    nifty50: number | null;
    nifty50_change_pct: number | null;
    sensex: number | null;
    sensex_change_pct: number | null;
    market_mood: string;
  };
  portfolio: {
    total_invested: number;
    total_holdings: number;
    top_gainers: { ticker: string; change_pct: number }[];
    top_losers: { ticker: string; change_pct: number }[];
    needs_rebalance: boolean;
  };
  top_recommendations: { ticker: string; action: string; confidence: number; reason?: string }[];
  alerts_summary: { critical: number; warning: number; info: number; total: number };
  opportunities: { ticker: string; type: string; score: number; reason: string }[];
  risks_to_watch: string[];
  action_items: string[];
}

interface Alert {
  id: string;
  category: string;
  severity: string;
  title: string;
  message: string;
  ticker: string | null;
  action_required: boolean;
  suggested_action: string | null;
}

export default function Advisor() {
  const [report, setReport] = useState<CIOReport | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    const token = getStoredToken();
    const headers = { Authorization: `Bearer ${token}` };

    Promise.allSettled([
      fetch("/api/v1/decisions/cio-report", { headers }).then(r => r.ok ? r.json() : null),
      fetch("/api/v1/decisions/alerts", { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([reportRes, alertsRes]) => {
      if (reportRes.status === "fulfilled" && reportRes.value) setReport(reportRes.value);
      if (alertsRes.status === "fulfilled" && alertsRes.value) setAlerts(alertsRes.value.alerts || []);
    }).finally(() => setLoading(false));
  }, []);

  async function askAI() {
    if (!query.trim()) return;
    setAiLoading(true);
    setAiResponse(null);

    const token = getStoredToken();
    try {
      // Extract ticker from query if possible (supports & in tickers like M&M, GVT&D)
      const tickerMatch = query.match(/\b([A-Z][A-Z0-9&]{1,14})\b/);
      const ticker = tickerMatch ? tickerMatch[1] : null;

      if (ticker) {
        // Use the AI analysis endpoint
        const res = await fetch(`/api/v1/ai/analyze/${ticker}`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          const summary = data.responses
            ?.map((r: any) => `**${r.agent_name}** (${r.score}/10): ${r.summary}`)
            .join("\n\n") || "Analysis complete.";
          setAiResponse(`Analysis for ${ticker}:\n\n${summary}`);
        } else {
          setAiResponse("Sorry, I couldn't analyze that ticker. Try a valid NSE stock symbol.");
        }
      } else {
        // Generic response for non-ticker queries
        setAiResponse(
          "I can analyze specific stocks for you. Try asking:\n" +
          "• 'Analyze RELIANCE'\n" +
          "• 'Should I buy TCS?'\n" +
          "• 'What about INFY?'\n\n" +
          "Just mention a stock ticker (in CAPS) and I'll run the AI agents on it."
        );
      }
    } catch {
      setAiResponse("Something went wrong. Please try again.");
    } finally {
      setAiLoading(false);
    }
  }

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><Spinner size="lg" /></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">AI Advisor</h1>
        <p className="text-sm text-slate-500">{report?.greeting || "Your daily investment intelligence"}</p>
      </div>

      {/* Ask AI — with voice input */}
      <Card>
        <div className="p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && query.trim() && askAI()}
              placeholder="Ask anything... e.g. 'Should I buy Reliance?' or 'Analyze my portfolio risk'"
              className="input flex-1"
            />
            <VoiceInput
              onResult={(text) => { setQuery(text); }}
              className="h-10 w-10 flex-shrink-0"
            />
            <button
              onClick={askAI}
              disabled={!query.trim() || aiLoading}
              className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50 transition flex-shrink-0"
            >
              {aiLoading ? "…" : "Ask"}
            </button>
          </div>
          {aiResponse && (
            <div className="mt-3 rounded-lg bg-slate-50 p-4 dark:bg-slate-800/50">
              <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{aiResponse}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Action Items */}
      {report?.action_items && report.action_items.length > 0 && (
        <Card>
          <CardHeader title="Today's Action Items" subtitle={report.report_date} />
          <div className="space-y-2">
            {report.action_items.map((item, i) => (
              <div key={i} className="flex items-start gap-3 rounded-lg bg-sky-50 px-4 py-3 dark:bg-sky-900/20">
                <span className="text-sm text-slate-800 dark:text-slate-200">{item}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Market + Portfolio Grid */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Market */}
        <Card>
          <CardHeader title="Market Overview" />
          {report?.market ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-300">Nifty 50</span>
                <div className="text-right">
                  <span className="font-mono text-sm font-semibold">{report.market.nifty50?.toLocaleString() || "—"}</span>
                  {report.market.nifty50_change_pct !== null && (
                    <span className={`ml-2 text-xs font-semibold ${report.market.nifty50_change_pct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {report.market.nifty50_change_pct >= 0 ? "+" : ""}{report.market.nifty50_change_pct.toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600 dark:text-slate-300">Sensex</span>
                <div className="text-right">
                  <span className="font-mono text-sm font-semibold">{report.market.sensex?.toLocaleString() || "—"}</span>
                  {report.market.sensex_change_pct !== null && (
                    <span className={`ml-2 text-xs font-semibold ${report.market.sensex_change_pct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {report.market.sensex_change_pct >= 0 ? "+" : ""}{report.market.sensex_change_pct.toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-slate-500">Market Mood:</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  report.market.market_mood === "bullish" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" :
                  report.market.market_mood === "bearish" ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" :
                  "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                }`}>
                  {report.market.market_mood}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Market data unavailable</p>
          )}
        </Card>

        {/* Portfolio Snapshot */}
        <Card>
          <CardHeader title="Portfolio Health" />
          {report?.portfolio ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-slate-500">Holdings</span>
                  <p className="font-semibold">{report.portfolio.total_holdings}</p>
                </div>
                <div>
                  <span className="text-slate-500">Invested</span>
                  <p className="font-semibold">₹{(report.portfolio.total_invested / 1e5).toFixed(1)}L</p>
                </div>
              </div>
              {report.portfolio.needs_rebalance && (
                <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
                  ⚠️ Portfolio needs rebalancing
                </div>
              )}
              {report.portfolio.top_gainers.length > 0 && (
                <div>
                  <span className="text-xs text-slate-500">Top Gainers Today</span>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {report.portfolio.top_gainers.map(g => (
                      <span key={g.ticker} className="rounded bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                        {g.ticker} +{g.change_pct.toFixed(1)}%
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {report.portfolio.top_losers.length > 0 && (
                <div>
                  <span className="text-xs text-slate-500">Top Losers Today</span>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {report.portfolio.top_losers.map(l => (
                      <span key={l.ticker} className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
                        {l.ticker} {l.change_pct.toFixed(1)}%
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400">No portfolio data</p>
          )}
        </Card>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card>
          <CardHeader title="Active Alerts" subtitle={`${alerts.length} alerts`} />
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {alerts.map(alert => (
              <div key={alert.id} className={`rounded-lg border px-4 py-3 ${
                alert.severity === "critical" ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20" :
                alert.severity === "warning" ? "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20" :
                "border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50"
              }`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{alert.title}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${
                    alert.severity === "critical" ? "bg-red-200 text-red-800 dark:bg-red-900 dark:text-red-200" :
                    alert.severity === "warning" ? "bg-amber-200 text-amber-800 dark:bg-amber-900 dark:text-amber-200" :
                    "bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                  }`}>{alert.severity}</span>
                </div>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{alert.message}</p>
                {alert.suggested_action && (
                  <p className="mt-1 text-xs font-medium text-sky-600 dark:text-sky-400">→ {alert.suggested_action}</p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Risks */}
      {report?.risks_to_watch && report.risks_to_watch.length > 0 && (
        <Card>
          <CardHeader title="Risks to Watch" />
          <ul className="space-y-2">
            {report.risks_to_watch.map((risk, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
                <span className="mt-0.5 text-amber-500">⚠️</span>
                {risk}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
