import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, CardHeader } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface CompanyInfo {
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
  description: string | null;
  website: string | null;
  employees: number | null;
  country: string;
  market_cap: number | null;
  pe_ratio: number | null;
  eps: number | null;
  dividend_yield: number | null;
  beta: number | null;
  high_52w: number | null;
  low_52w: number | null;
}

interface Quote {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  day_high: number | null;
  day_low: number | null;
  prev_close: number | null;
}

interface PricePoint {
  date: string;
  close: number;
}

const formatINR = (val: number) => `₹${val.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
const formatCrores = (val: number | null) => {
  if (!val) return "—";
  if (val >= 1e12) return `₹${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e7) return `₹${(val / 1e7).toFixed(0)} Cr`;
  return formatINR(val);
};

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const [company, setCompany] = useState<CompanyInfo | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    const token = getStoredToken();

    async function fetchAll() {
      const headers = { Authorization: `Bearer ${token}` };

      // Fetch in parallel
      const [companyRes, quoteRes, historyRes] = await Promise.allSettled([
        fetch(`/api/v1/market/company/${ticker}`, { headers }),
        fetch(`/api/v1/market/quote/${ticker}`, { headers }),
        fetch(`/api/v1/prices/history/${ticker}?days=180`, { headers }),
      ]);

      if (companyRes.status === "fulfilled" && companyRes.value.ok)
        setCompany(await companyRes.value.json());
      if (quoteRes.status === "fulfilled" && quoteRes.value.ok)
        setQuote(await quoteRes.value.json());
      if (historyRes.status === "fulfilled" && historyRes.value.ok)
        setPriceHistory(await historyRes.value.json());

      setLoading(false);
    }

    fetchAll();
  }, [ticker]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const isPositive = (quote?.change ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{ticker}</h1>
            {company?.sector && <span className="badge-blue">{company.sector}</span>}
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {company?.name || ticker} • {company?.industry || ""}
          </p>
        </div>
        <Link to="/portfolio" className="btn-secondary text-sm">
          ← Back to Portfolio
        </Link>
      </div>

      {/* Price + Quote */}
      {quote && (
        <Card>
          <div className="flex items-baseline gap-4">
            <span className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {formatINR(quote.price)}
            </span>
            <span className={`text-lg font-semibold ${isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
              {isPositive ? "+" : ""}{quote.change.toFixed(2)} ({isPositive ? "+" : ""}{quote.change_pct.toFixed(2)}%)
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4 text-sm">
            <div><span className="text-slate-500">Day High</span><br /><span className="font-mono">{quote.day_high ? formatINR(quote.day_high) : "—"}</span></div>
            <div><span className="text-slate-500">Day Low</span><br /><span className="font-mono">{quote.day_low ? formatINR(quote.day_low) : "—"}</span></div>
            <div><span className="text-slate-500">Prev Close</span><br /><span className="font-mono">{quote.prev_close ? formatINR(quote.prev_close) : "—"}</span></div>
            <div><span className="text-slate-500">Volume</span><br /><span className="font-mono">{quote.volume.toLocaleString()}</span></div>
          </div>
        </Card>
      )}

      {/* Price chart */}
      {priceHistory.length > 0 && (
        <Card>
          <CardHeader title="Price History" subtitle="Last 6 months" />
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceHistory} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  tickFormatter={(d: string) => new Date(d).toLocaleDateString("en-IN", { month: "short" })}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  tickLine={false}
                  interval={Math.floor(priceHistory.length / 5)}
                />
                <YAxis
                  tickFormatter={(v: number) => `₹${v.toFixed(0)}`}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #475569", borderRadius: "8px" }}
                  formatter={(value: number) => [formatINR(value), "Close"]}
                  labelFormatter={(d: string) => new Date(d).toLocaleDateString("en-IN")}
                />
                <Line type="monotone" dataKey="close" stroke="#0ea5e9" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* Company fundamentals */}
      {company && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title="Key Metrics" />
            <div className="grid grid-cols-2 gap-y-3 text-sm">
              <div><span className="text-slate-500">Market Cap</span><br /><span className="font-semibold">{formatCrores(company.market_cap)}</span></div>
              <div><span className="text-slate-500">P/E Ratio</span><br /><span className="font-semibold">{company.pe_ratio?.toFixed(2) || "—"}</span></div>
              <div><span className="text-slate-500">EPS</span><br /><span className="font-semibold">{company.eps ? formatINR(company.eps) : "—"}</span></div>
              <div><span className="text-slate-500">Beta</span><br /><span className="font-semibold">{company.beta?.toFixed(2) || "—"}</span></div>
              <div><span className="text-slate-500">52W High</span><br /><span className="font-semibold">{company.high_52w ? formatINR(company.high_52w) : "—"}</span></div>
              <div><span className="text-slate-500">52W Low</span><br /><span className="font-semibold">{company.low_52w ? formatINR(company.low_52w) : "—"}</span></div>
              <div><span className="text-slate-500">Dividend Yield</span><br /><span className="font-semibold">{company.dividend_yield ? `${(company.dividend_yield * 100).toFixed(2)}%` : "—"}</span></div>
              <div><span className="text-slate-500">Employees</span><br /><span className="font-semibold">{company.employees?.toLocaleString() || "—"}</span></div>
            </div>
          </Card>

          <Card>
            <CardHeader title="About" />
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {company.description ? company.description.slice(0, 500) + (company.description.length > 500 ? "…" : "") : "No description available."}
            </p>
            {company.website && (
              <a href={company.website} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-sm text-sky-500 hover:text-sky-400">
                {company.website} ↗
              </a>
            )}
          </Card>
        </div>
      )}

      {/* Corporate Actions */}
      <CorporateActionsSection ticker={ticker || ""} />

      {/* Financial Statements */}
      <FinancialsSection ticker={ticker || ""} />
    </div>
  );
}


// ── Financials Section ────────────────────────────────────────────────────────

function FinancialsSection({ ticker }: { ticker: string }) {
  const [data, setData] = useState<{ period_date: string; data: Record<string, number> }[]>([]);
  const [stmtType, setStmtType] = useState<"income" | "balance" | "cashflow">("income");
  const [period, setPeriod] = useState<"quarterly" | "annual">("quarterly");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    const token = getStoredToken();
    fetch(`/api/v1/financials/${ticker}?type=${stmtType}&period=${period}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setData(d.statements); else setData([]); })
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [ticker, stmtType, period]);

  const formatNum = (n: number) => {
    if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(1)} Cr`;
    if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(1)} L`;
    return `₹${n.toLocaleString("en-IN")}`;
  };

  // Get top 8 line items from first period
  const lineItems = data.length > 0
    ? Object.keys(data[0].data).slice(0, 10)
    : [];

  return (
    <Card>
      <CardHeader title="Financial Statements" subtitle="Quarterly and annual data from Yahoo Finance" />

      {/* Tabs */}
      <div className="mb-4 flex flex-wrap gap-2">
        {(["income", "balance", "cashflow"] as const).map(t => (
          <button
            key={t}
            onClick={() => setStmtType(t)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${stmtType === t ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"}`}
          >
            {t === "income" ? "Income" : t === "balance" ? "Balance Sheet" : "Cash Flow"}
          </button>
        ))}
        <span className="mx-2 text-slate-300">|</span>
        {(["quarterly", "annual"] as const).map(p => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${period === p ? "bg-sky-500 text-white" : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"}`}
          >
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-32 items-center justify-center"><Spinner size="md" /></div>
      ) : data.length === 0 ? (
        <p className="text-sm text-slate-400 py-8 text-center">No financial data available for {ticker}.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700">
                <th className="py-2 pr-4 text-left font-medium text-slate-500">Line Item</th>
                {data.slice(0, 4).map(d => (
                  <th key={d.period_date} className="py-2 px-2 text-right font-medium text-slate-500">
                    {new Date(d.period_date).toLocaleDateString("en-IN", { month: "short", year: "2-digit" })}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lineItems.map(item => (
                <tr key={item} className="border-b border-slate-100 dark:border-slate-700/50">
                  <td className="py-2 pr-4 text-slate-700 dark:text-slate-300 truncate max-w-[200px]">{item}</td>
                  {data.slice(0, 4).map(d => (
                    <td key={d.period_date} className="py-2 px-2 text-right font-mono text-slate-600 dark:text-slate-400">
                      {d.data[item] !== undefined ? formatNum(d.data[item]) : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}


// ── Corporate Actions Section ─────────────────────────────────────────────────

function CorporateActionsSection({ ticker }: { ticker: string }) {
  const [dividends, setDividends] = useState<{ date: string; amount: number }[]>([]);
  const [splits, setSplits] = useState<{ date: string; ratio_from: number; ratio_to: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    const token = getStoredToken();
    fetch(`/api/v1/corporate-actions/${ticker}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          setDividends(d.dividends || []);
          setSplits(d.splits || []);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) return null; // Don't show section while loading
  if (dividends.length === 0 && splits.length === 0) return null; // No data = hide section

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* Dividends */}
      {dividends.length > 0 && (
        <Card>
          <CardHeader title="Dividend History" subtitle={`${dividends.length} dividends`} />
          <div className="max-h-48 overflow-y-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="py-2 text-left text-slate-500">Date</th>
                  <th className="py-2 text-right text-slate-500">Amount</th>
                </tr>
              </thead>
              <tbody>
                {dividends.slice(0, 20).map((d, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-700/50">
                    <td className="py-1.5 text-slate-700 dark:text-slate-300">
                      {new Date(d.date).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}
                    </td>
                    <td className="py-1.5 text-right font-mono text-emerald-600 dark:text-emerald-400">
                      ₹{d.amount.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Splits */}
      {splits.length > 0 && (
        <Card>
          <CardHeader title="Stock Splits" subtitle={`${splits.length} splits`} />
          <div className="space-y-2">
            {splits.map((s, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-700/50">
                <span className="text-xs text-slate-600 dark:text-slate-300">
                  {new Date(s.date).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}
                </span>
                <span className="font-mono text-sm font-semibold text-sky-600 dark:text-sky-400">
                  {s.ratio_from}:{s.ratio_to}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
