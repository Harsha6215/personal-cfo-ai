import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, Column } from "@/components/ui/Table";
import { Spinner } from "@/components/ui/Spinner";
import { PortfolioChart } from "@/components/ui/PortfolioChart";
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
      <Link to={`/stock/${row.ticker}`} className="block hover:opacity-80">
        <p className="font-medium text-sky-600 dark:text-sky-400 hover:underline">{row.ticker}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{row.name}</p>
      </Link>
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
  const [showAddForm, setShowAddForm] = useState(false);

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

      {/* Portfolio performance chart */}
      <Card>
        <CardHeader title="Portfolio Performance" subtitle="Total portfolio value over time" />
        <PortfolioChart days={365} />
      </Card>

      {/* Holdings table */}
      <Card>
        <CardHeader
          title={`${data.portfolio_name}`}
          subtitle={pricesLoading ? "Fetching live prices…" : `${data.total_holdings} positions • Live prices from Yahoo Finance`}
        />
        {/* Add Holding button */}
        <div className="px-4 pb-3 flex gap-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white hover:bg-sky-600 transition"
          >
            + Add Holding
          </button>
          <Link to="/import" className="rounded-lg border border-slate-300 dark:border-slate-600 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition">
            Import CSV
          </Link>
        </div>

        {/* Add Holding Form */}
        {showAddForm && (
          <AddHoldingForm
            portfolioId={data.portfolio_id}
            onAdded={() => { setShowAddForm(false); window.location.reload(); }}
            onCancel={() => setShowAddForm(false)}
          />
        )}

        <Table
          columns={columns}
          data={data.holdings}
          loading={pricesLoading}
          emptyMessage="No holdings yet. Add one manually or import your broker CSV."
        />
      </Card>
    </div>
  );
}


// ── Add Holding Form ──────────────────────────────────────────────────────────

function AddHoldingForm({
  portfolioId,
  onAdded,
  onCancel,
}: {
  portfolioId: string;
  onAdded: () => void;
  onCancel: () => void;
}) {
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [assetType, setAssetType] = useState("STOCK");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !name || !quantity || !price) {
      setError("All fields are required");
      return;
    }
    setSubmitting(true);
    setError("");

    const token = getStoredToken();
    try {
      const res = await fetch(`/api/v1/portfolios/${portfolioId}/add-holding`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          name,
          quantity: parseFloat(quantity),
          price: parseFloat(price),
          asset_type: assetType,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to add holding");
      }

      onAdded();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-4 mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Ticker</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="input text-sm"
            placeholder="RELIANCE"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input text-sm"
            placeholder="Reliance Industries"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Quantity</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="input text-sm"
            placeholder="10"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Buy Price (₹)</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="input text-sm"
            placeholder="2500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Type</label>
          <select
            value={assetType}
            onChange={(e) => setAssetType(e.target.value)}
            className="input text-sm"
          >
            <option value="STOCK">Stock</option>
            <option value="ETF">ETF</option>
            <option value="MUTUAL_FUND">Mutual Fund</option>
            <option value="BOND">Bond</option>
            <option value="GOLD">Gold</option>
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50 transition"
          >
            {submitting ? "…" : "Add"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
          >
            Cancel
          </button>
        </div>
      </form>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  );
}
