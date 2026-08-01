import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, Column } from "@/components/ui/Table";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";

interface Holding {
  asset_id: string;
  ticker: string;
  name: string;
  asset_type: string;
  quantity: number;
  average_cost: number;
  invested_value: number;
  // Live data (filled after market fetch)
  current_price?: number;
  current_value?: number;
  pnl?: number;
  pnl_pct?: number;
}

interface PortfolioData {
  portfolio_id: string;
  portfolio_name: string;
  total_invested: number;
  total_holdings: number;
  total_events: number;
  holdings: Holding[];
}

const formatINR = (val: number) => `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const columns: Column<Holding>[] = [
  {
    key: "ticker",
    header: "Ticker",
    render: (_, row) => (
      <div>
        <p className="font-medium text-slate-900 dark:text-slate-100">{row.ticker}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{row.name}</p>
      </div>
    ),
  },
  { key: "asset_type", header: "Type", width: "70px" },
  {
    key: "quantity",
    header: "Qty",
    align: "right",
    render: (val) => <span className="font-mono">{Number(val).toLocaleString()}</span>,
  },
  {
    key: "average_cost",
    header: "Avg Cost",
    align: "right",
    render: (val) => <span className="font-mono text-xs">{formatINR(Number(val))}</span>,
  },
  {
    key: "current_price",
    header: "LTP",
    align: "right",
    render: (val) => val ? <span className="font-mono font-medium">{formatINR(Number(val))}</span> : <span className="text-xs text-slate-400">—</span>,
  },
  {
    key: "invested_value",
    header: "Invested",
    align: "right",
    render: (val) => <span className="font-mono text-xs">{formatINR(Number(val))}</span>,
  },
  {
    key: "current_value",
    header: "Current",
    align: "right",
    render: (val) => val ? <span className="font-mono font-medium">{formatINR(Number(val))}</span> : <span className="text-xs text-slate-400">—</span>,
  },
  {
    key: "pnl",
    header: "P&L",
    align: "right",
    render: (val, row) => {
      if (val === undefined || val === null) return <span className="text-xs text-slate-400">—</span>;
      const isPositive = Number(val) >= 0;
      return (
        <div className="text-right">
          <p className={`font-mono text-sm font-medium ${isPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
            {isPositive ? "+" : ""}{formatINR(Number(val))}
          </p>
          <p className={`font-mono text-xs ${isPositive ? "text-emerald-500" : "text-red-500"}`}>
            {isPositive ? "+" : ""}{row.pnl_pct?.toFixed(2)}%
          </p>
        </div>
      );
    },
  },
];

export default function Portfolio() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCurrentValue, setTotalCurrentValue] = useState<number | null>(null);
  const [totalPnl, setTotalPnl] = useState<number | null>(null);

  useEffect(() => {
    async function fetchPortfolio() {
      try {
        const token = getStoredToken();

        const res = await fetch("/api/v1/portfolios", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch portfolios");

        const portfolios = await res.json();
        if (portfolios.length === 0) {
          setError("No portfolio found. Import your holdings first.");
          setLoading(false);
          return;
        }

        const holdingsRes = await fetch(`/api/v1/portfolios/${portfolios[0].id}/holdings`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!holdingsRes.ok) throw new Error("Failed to fetch holdings");

        const holdingsData: PortfolioData = await holdingsRes.json();
        setData(holdingsData);
        setLoading(false);

        // Fetch live prices for each holding
        setPricesLoading(true);
        const updatedHoldings = [...holdingsData.holdings];
        let totalCV = 0;
        let totalPL = 0;

        for (let i = 0; i < updatedHoldings.length; i++) {
          try {
            const quoteRes = await fetch(`/api/v1/market/quote/${updatedHoldings[i].ticker}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (quoteRes.ok) {
              const quote = await quoteRes.json();
              const currentPrice = quote.price;
              const currentValue = currentPrice * updatedHoldings[i].quantity;
              const pnl = currentValue - updatedHoldings[i].invested_value;
              const pnlPct = updatedHoldings[i].invested_value > 0
                ? (pnl / updatedHoldings[i].invested_value) * 100
                : 0;

              updatedHoldings[i] = {
                ...updatedHoldings[i],
                current_price: currentPrice,
                current_value: Math.round(currentValue * 100) / 100,
                pnl: Math.round(pnl * 100) / 100,
                pnl_pct: Math.round(pnlPct * 100) / 100,
              };
              totalCV += currentValue;
              totalPL += pnl;
            }
          } catch {
            // Skip failed quotes
          }
        }

        setData({ ...holdingsData, holdings: updatedHoldings });
        setTotalCurrentValue(Math.round(totalCV * 100) / 100);
        setTotalPnl(Math.round(totalPL * 100) / 100);
        setPricesLoading(false);
      } catch (err: any) {
        setError(err.message);
        setLoading(false);
      }
    }

    fetchPortfolio();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <p className="text-slate-500 dark:text-slate-400">{error}</p>
          <a href="/import" className="mt-2 inline-block text-sm text-sky-500 hover:text-sky-400">
            Go to Import →
          </a>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const pnlIsPositive = (totalPnl ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Invested</p>
            <p className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100">
              {formatINR(data.total_invested)}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Current Value</p>
            <p className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100">
              {totalCurrentValue !== null ? formatINR(totalCurrentValue) : <Spinner size="sm" />}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Total P&L</p>
            {totalPnl !== null ? (
              <p className={`mt-1 text-xl font-bold ${pnlIsPositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                {pnlIsPositive ? "+" : ""}{formatINR(totalPnl)}
              </p>
            ) : (
              <Spinner size="sm" />
            )}
            {totalPnl !== null && data.total_invested > 0 && (
              <p className={`text-xs ${pnlIsPositive ? "text-emerald-500" : "text-red-500"}`}>
                {pnlIsPositive ? "+" : ""}{((totalPnl / data.total_invested) * 100).toFixed(2)}%
              </p>
            )}
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Holdings</p>
            <p className="mt-1 text-xl font-bold text-slate-900 dark:text-slate-100">
              {data.total_holdings}
            </p>
          </div>
        </Card>
      </div>

      {/* Holdings table */}
      <Card>
        <CardHeader
          title={`${data.portfolio_name}`}
          subtitle={pricesLoading ? "Fetching live prices…" : `${data.total_holdings} positions • Live prices from Yahoo Finance`}
        />
        <Table
          columns={columns}
          data={data.holdings}
          loading={pricesLoading}
          emptyMessage="No holdings yet. Import your broker CSV to get started."
        />
      </Card>
    </div>
  );
}
