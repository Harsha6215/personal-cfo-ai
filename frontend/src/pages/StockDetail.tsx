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
    </div>
  );
}
